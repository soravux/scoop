#
#    This file is part of Scalable COncurrent Operations in Python (SCOOP).
#
#    SCOOP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    SCOOP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with SCOOP. If not, see <http://www.gnu.org/licenses/>.
#
from collections import deque, defaultdict
import os
import time
import tempfile
import sys
import math
from functools import partial
import traceback

import greenlet

from ._types import Future, FutureQueue, CallbackType, UnrecognizedFuture
import scoop

# Backporting collection features
if sys.version_info < (2, 7):
    from scoop.backports.newCollections import deque

# Future currently running in greenlet
current = None
# Dictionary of existing futures
futureDict = {}
# Queue of futures pending execution
execQueue = None
# Execution Statistics
class _stat(deque):
    def __init__(self, *args, **kargs):
        self._sum = 0
        self._squared_sum = 0
        super(_stat, self).__init__(*args, maxlen=10, **kargs)

    def appendleft(self, x):
        try:
            ln_x = math.log(x)
        except ValueError:
            # Make it smaller than possible clock precision
            ln_x = 1e-100
        if len(self) >= self.maxlen:
            self._sum -= math.log(self[-1])
            self._squared_sum -= math.log(self[-1]) ** 2
        self._sum += ln_x
        self._squared_sum += ln_x ** 2
        super(_stat, self).appendleft(x)

    def mean(self):
        ourSize = len(self)
        if ourSize > 3:
            return self._sum / ourSize
        return float("inf")

    def std(self):
        ourSize = len(self)
        if ourSize > 3:
            return math.sqrt(ourSize * self._squared_sum - self._sum ** 2) / ourSize
        return float("inf")

    def mode(self):
        """Computes the mode of a log-normal distribution built with the stats data."""
        mu = self.mean()
        sigma = self.std()
        ret_val = math.exp(mu - sigma**2)
        if math.isnan(ret_val):
            ret_val = float("inf")
        return ret_val

    def median(self):
        """Computes the median of a log-normal distribution built with the stats data."""
        mu = self.mean()
        ret_val = math.exp(mu)
        if math.isnan(ret_val):
            ret_val = float("inf")
        return ret_val


def advertiseBrokerWorkerDown(exctype, value, traceback):
    """Hook advertising the broker if an impromptu shutdown is occuring."""
    if not scoop.SHUTDOWN_REQUESTED:
        execQueue.shutdown()
    sys.__excepthook__(exctype, value, traceback)


def init_debug():
    """Initialise debug_stats and QueueLength (this is not a reset)"""
    global debug_stats
    global QueueLength
    if debug_stats is None:
        list_defaultdict = partial(defaultdict, list)
        debug_stats = defaultdict(list_defaultdict)
        QueueLength = []


def delFutureById(futureId, parentId):
    """Delete future on id basis"""
    try:
        del futureDict[futureId]
    except KeyError:
        pass
    try:
        toDel = [a for a in futureDict[parentId].children if a.id == futureId]
        for f in toDel:
            del futureDict[parentId].children[f]
    except KeyError:
        pass


def delFuture(afuture):
    """Delete future afuture"""
    try:
        del futureDict[afuture.id]
    except KeyError:
        raise UnrecognizedFuture(
            "The future ID {0} was unavailable in the "
            "futureDict of worker {1}".format(afuture.id, scoop.worker))
    if afuture.id[0] == scoop.worker and afuture.parentId != (-1, 0):
        try:
            del futureDict[afuture.parentId].children[afuture]
        except KeyError:
            # This does not raise an exception as this happens when a future is
            # resent after being lost
            scoop.logger.warning(
                "Orphan future {0} being deleted from worker {1}"
                .format(afuture.id, scoop.worker))


def runFuture(future):
    """Callable greenlet in charge of running tasks."""
    global debug_stats
    global QueueLength
    if scoop.DEBUG:
        init_debug()  # in case _control is imported before scoop.DEBUG was set
        debug_stats[future.id]['start_time'].append(time.time())
    future.waitTime = future.stopWatch.get()
    future.stopWatch.reset()
    # Get callback Group ID and assign the broker-wide unique executor ID
    try:
        uniqueReference = [cb.groupID for cb in future.callback][0]
    except IndexError:
        uniqueReference = None
    future.executor = (scoop.worker, uniqueReference)
    try:
        future.resultValue = future.callable(*future.args, **future.kargs)
    except BaseException as err:
        future.exceptionValue = err
        future.exceptionTraceback = str(traceback.format_exc())
        scoop.logger.debug(
            "The following error occured on a worker:\n%r\n%s",
            err,
            traceback.format_exc(),
        )
    future.executionTime = future.stopWatch.get()
    future.isDone = True

    # Update the worker inner work statistics
    if future.executionTime != 0. and hasattr(future.callable, '__name__'):
        execStats[hash(future.callable)].appendleft(future.executionTime)

    # Set debugging informations if needed
    if scoop.DEBUG:
        t = time.time()
        debug_stats[future.id]['end_time'].append(t)
        debug_stats[future.id].update({
            'executionTime': future.executionTime,
            'worker': scoop.worker,
            'creationTime': future.creationTime,
            'callable': str(future.callable.__name__)
                if hasattr(future.callable, '__name__')
                else 'No name',
           'parent': future.parentId
        })
        QueueLength.append((t, len(execQueue), execQueue.timelen(execQueue)))

    # Run callback (see http://www.python.org/dev/peps/pep-3148/#future-objects)
    future._execute_callbacks(CallbackType.universal)

    return future


def runController(callable_, *args, **kargs):
    """Callable greenlet implementing controller logic."""
    global execQueue

    # initialize and run root future
    rootId = (-1, 0)

    # initialise queue
    if execQueue is None:
        execQueue = FutureQueue()

        sys.excepthook = advertiseBrokerWorkerDown

        if scoop.DEBUG:
            from scoop import _debug
            _debug.redirectSTDOUTtoDebugFile()

        # TODO: Make that a function
        # Wait until we received the main module if we are a headless slave
        headless = scoop.CONFIGURATION.get("headless", False)
        if not scoop.MAIN_MODULE:
            # If we're not the origin and still don't have our main_module,
            # wait for it and then import it as module __main___
            main = scoop.shared.getConst('__MAIN_MODULE__', timeout=float('inf'))
            directory_name = tempfile.mkdtemp()
            os.chdir(directory_name)
            scoop.MAIN_MODULE = main.writeFile(directory_name)
            from .bootstrap.__main__ import Bootstrap as SCOOPBootstrap
            newModule = SCOOPBootstrap.setupEnvironment()
            sys.modules['__main__'] = newModule
        elif scoop.IS_ORIGIN and headless and scoop.MAIN_MODULE:
            # We're the origin, share our main_module
            scoop.shared.setConst(
                __MAIN_MODULE__=scoop.encapsulation.ExternalEncapsulation(
                    scoop.MAIN_MODULE,
                )
            )
            # TODO: use modulefinder to share every local dependency of
            # main module

    # launch future if origin or try to pickup a future if slave worker
    if scoop.IS_ORIGIN:
        future = Future(rootId, callable_, *args, **kargs)
    else:
        future = execQueue.pop()

    future.greenlet = greenlet.greenlet(runFuture)
    future = future._switch(future)

    if scoop.DEBUG:
        lastDebugTs = time.time()

    while not scoop.IS_ORIGIN or future.parentId != rootId or not future._ended():
        if scoop.DEBUG and time.time() - lastDebugTs > scoop.TIME_BETWEEN_PARTIALDEBUG:
            _debug.writeWorkerDebug(
                debug_stats,
                QueueLength,
                "debug/partial-{0}".format(
                    round(time.time(), -1)
                )
            )
            lastDebugTs = time.time()

        # At this point , the future is either completed or in progress
        # in progress => its runFuture greenlet is in progress

        # process future and get new future / result future
        waiting_parent = False
        if future.isDone:
            if future.isReady:
                # future is completely processed and ready to be returned This return is
                # executed only if the parent is waiting for this particular future.
                # Note: orphaned futures are caused by... what again?
                execQueue.sendReadyStatus(future)
                if future.index is not None:
                    # This means that this particular future is being waited upon by a
                    # parent (see futures._waitAny())
                    if future.parentId in futureDict:
                        parent = futureDict[future.parentId]
                        if parent.exceptionValue is None:
                            waiting_parent = True
            else:
                execQueue.finalizeFuture(future)

        if future.isReady and waiting_parent:
            # This means that this future must be returned to the parent future greenlet
            # by this, one of 2 things happen, the parent completes execution and
            # returns itself along with its results and isDone set to True, or, in case
            # it has spawned a sub-future or needs to wait on another future, it returns
            # itself in an inprogress state (isDone = False)
            future = parent._switch(future)
        else:
            # This means that the future is either ready and the parent is not waiting,
            # or the future is in progress. This happens when the future is a parent
            # future whose greenlet has returned itself in an incomplete manner. check
            # the above comment
            # 
            # In both the above cases, the future can safely be dropped/ignored and the
            # next future picked up from the queue for processing.
            future = execQueue.pop()

        if not future._ended() and future.greenlet is None:
            # This checks for the case of a not-yet-started-execution future that is
            # returned from the queue, (This can only happen if execQueue.pop is called)
            # and starts the execution
            future.greenlet = greenlet.greenlet(runFuture)
            future = future._switch(future)

    # Special case of removing the root future from the futureDict
    scoop._control.delFuture(future)

    execQueue.shutdown()
    if future.exceptionValue:
        print(future.exceptionTraceback)
        sys.exit(1)
    return future.resultValue


execStats = defaultdict(_stat)

debug_stats = None
QueueLength = None
if scoop.DEBUG:
    init_debug()
