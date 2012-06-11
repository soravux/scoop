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
from collections import deque
import greenlet
import os
from .types import Future, FutureId, FutureQueue
import scoop

# Set module-scope variables about this controller
worker = (scoop.WORKER_NAME, scoop.BROKER_NAME) # worker future id
rank = 0                                        # rank id for next future
is_origin = scoop.IS_ORIGIN                     # is the worker the origin?
current = None                                  # future currently running in greenlet
futureDict = {}                                 # dictionary of existing futures
execQueue = None                                # queue of futures pending execution
if scoop.DEBUG:
    import time
    stats = {}
    QueueLength = []

# This is the callable greenlet for running futures.
def runFuture(future):
    if scoop.DEBUG:
        stats.setdefault(future.id, {}).setdefault('start_time', []).append(time.time())
    future.waitTime = future.stopWatch.get()
    future.stopWatch.reset()
    try:
        future.resultValue = future.callable(*future.args, **future.kargs)    
    except Exception as err:
        future.exceptionValue = err
    future.executionTime = future.stopWatch.get()
    assert future.done(), "callable must return a value!"
    
    # Set debugging informations if needed
    if scoop.DEBUG:
        t = time.time()
        stats[future.id].setdefault('end_time', []).append(t)
        stats[future.id].update({'executionTime': future.executionTime,
                               'worker': worker,
                               'creationTime': future.creationTime,
                               'callable': str(future.callable.__name__)
                                    if hasattr(future.callable, '__name__')
                                    else 'No name',
                               'parent': future.parentId})
        QueueLength.append((t, len(execQueue)))
    # Run callback (see http://www.python.org/dev/peps/pep-3148/#future-objects)
    for callback in future.callback:
        try: callback(future)
        except: pass # Ignored callback exception as stated in PEP 3148
    return future

# This is the callable greenlet that implements the controller logic.
def runController(callable, *args, **kargs):
    global execQueue
    # initialize and run root future
    rootId = FutureId(-1,0)
    
    # initialise queue
    if execQueue == None:
        execQueue = deque() if len(scoop.BROKER_ADDRESS) == 0  else FutureQueue()
    
    # launch future if origin or try to pickup a future if slave worker
    if is_origin == True:
        future = Future(rootId, callable, *args, **kargs)
    else:
        future = execQueue.pop()
        
    future.greenlet = greenlet.greenlet(runFuture)
    future = future._switch(future)
    
    while future.parentId != rootId or not future.done() or is_origin == False:
        # process future
        if future.done():
            # future is finished
            if future.id.worker != worker:
                # future is not local
                execQueue.sendResult(future)
                future = execQueue.pop()
            else:
                # future is local, parent is waiting
                if future.index != None:
                    parent = futureDict[future.parentId]
                    if parent.exceptionValue == None:
                        future = parent._switch(future)
                    else:
                        future = execQueue.pop()
                else:
                    execQueue.append(future)
                    future = execQueue.pop()
        else:
            # future is in progress; run next future from pending execution queue.
            future = execQueue.pop()

        if future.resultValue == None and future.greenlet == None:
            # initialize if the future hasn't started
            future.greenlet = greenlet.greenlet(runFuture)
            future = future._switch(future)

    execQueue.socket.shutdown()
    if future.exceptionValue:
        raise future.exceptionValue
    return future.resultValue
