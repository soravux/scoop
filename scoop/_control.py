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
from __future__ import print_function
from collections import deque, defaultdict
import os
from functools import partial

import greenlet

from ._types import Future, FutureId, FutureQueue, CallbackType
import scoop
import reduction

# Future currently running in greenlet
current = None
# Dictionary of existing futures
futureDict = {}
# Queue of futures pending execution
execQueue = None
# Statistics of execution
class _stat(deque):
    def __init__(self, *args, **kargs):
        self._sum = 0
        super(_stat, self).__init__(*args,maxlen = 10, **kargs)

    def appendleft(self, x):
        if len(self) >= self.maxlen:
            self._sum -= self[-1]
        self._sum += x
        super(_stat, self).appendleft(x)

    def mean(self):
        if len(self) > 3:
            return self._sum / len(self)
        return float("inf")

execStats = defaultdict(_stat)
if scoop.DEBUG:
    import time
    list_defaultdict = partial(defaultdict, list)
    debug_stats = defaultdict(list_defaultdict)
    QueueLength = []
    
def delFuture(futureId, parentId):
    try:
        del futureDict[futureId]
    except KeyError:
        pass
    try:
        while futureId in (a.id for a in futureDict[parentId].children):
            toDel = [a.id for a in futureDict[parentId].children].index(futureId)
            futureDict[parentId].children.pop(toDel)
    except KeyError:
        pass

# This is the callable greenlet for running tasks.
def runFuture(future):
    if scoop.DEBUG:
        debug_stats[future.id]['start_time'].append(time.time())
    future.waitTime = future.stopWatch.get()
    future.stopWatch.reset()
    # Get callback Group ID and assign the broker-wide unique executor ID
    try:
        uniqueReference = [cb.groupID for cb in future.callback][0]
    except IndexError:
        uniqueReference = None
    future.executor = (scoop.worker, next(reduction.sequence[uniqueReference]), uniqueReference)
    try:
        future.resultValue = future.callable(*future.args, **future.kargs)
    except Exception as err:
        future.exceptionValue = err
    future.executionTime = future.stopWatch.get()
    assert future.done(), "callable must return a value!"

    # Update the worker inner work statistics
    if future.executionTime != 0. and hasattr(future.callable, '__name__'):
        execStats[future.callable.__name__].appendleft(future.executionTime)

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
        QueueLength.append((t, execQueue.timelen(execQueue)))

    # Run callback (see http://www.python.org/dev/peps/pep-3148/#future-objects)
    for callback in future.callback:
        if future.parentId.worker == scoop.worker or \
        callback.callbackType == CallbackType.universal:
            try: callback.func(future)
            except: pass # Ignored callback exception as stated in PEP 3148

    # Delete references to the future
    future._delete()

    return future

# This is the callable greenlet that implements the controller logic.
def runController(callable, *args, **kargs):
    global execQueue
    # initialize and run root future
    rootId = FutureId(-1,0)
    
    # initialise queue
    if execQueue is None:
        execQueue = FutureQueue()
    
    # launch future if origin or try to pickup a future if slave worker
    if scoop.IS_ORIGIN:
        future = Future(rootId, callable, *args, **kargs)
    else:
        future = execQueue.pop()
        
    future.greenlet = greenlet.greenlet(runFuture)
    future = future._switch(future)
    
    while future.parentId != rootId or not future.done() or not scoop.IS_ORIGIN:
        # process future
        if future.done():
            # future is finished
            if future.id.worker != scoop.worker:
                # future is not local
                execQueue.sendResult(future)
                future = execQueue.pop()
            else:
                # future is local, parent is waiting
                if future.index is not None:
                    parent = futureDict[future.parentId]
                    if parent.exceptionValue is None:
                        future = parent._switch(future)
                    else:
                        future = execQueue.pop()
                else:
                    future = execQueue.pop()
        else:
            # future is in progress; run next future from pending execution queue.
            future = execQueue.pop()

        if future.resultValue is None and future.greenlet is None:
            # initialize if the future hasn't started
            future.greenlet = greenlet.greenlet(runFuture)
            future = future._switch(future)

    execQueue.shutdown()
    if future.exceptionValue:
        raise future.exceptionValue
    return future.resultValue
