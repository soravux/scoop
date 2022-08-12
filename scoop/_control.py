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

from ._types import Future, FutureQueue, CallbackType
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
        pass
    try:
        del futureDict[afuture.parentId].children[afuture]
    except KeyError:
        pass


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

    # Delete references to the future
    future._delete()

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
        # process future
        if future._ended():
            # future is finished
            if future.id[0] != scoop.worker:
                # future is not local
                execQueue.sendResult(future)
                future = execQueue.pop()
            else:
                # future is local, parent is waiting
                if future.index is not None:
                    try:
                        parent = futureDict[future.parentId]
                    except KeyError:
                        # Job has no parent here (probably children restart)
                        future = execQueue.pop()
                    else:
                        if parent.exceptionValue is None:
                            future = parent._switch(future)
                        else:
                            future = execQueue.pop()
                else:
                    future = execQueue.pop()
        else:
            # future is in progress; run next future from pending execution queue.
            future = execQueue.pop()

        if not future._ended() and future.greenlet is None:
            # initialize if the future hasn't started
            future.greenlet = greenlet.greenlet(runFuture)
            future = future._switch(future)

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
