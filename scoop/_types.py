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
from collections import namedtuple, deque
import itertools
import time
import sys
import greenlet
import scoop
from scoop._comm import Communicator, Shutdown

# Backporting collection features
if sys.version_info < (2, 7):
    from scoop.backports.newCollections import Counter
else:
    from collections import Counter


class CallbackType:
    """Type of groups enumeration."""
    standard = "standard"
    universal = "universal"


# This class encapsulates a stopwatch that returns elapse time in seconds.
class StopWatch(object):
    # initialize stopwatch.
    def __init__(self):
        self.totalTime = 0
        self.startTime = time.time()
        self.halted = False
    # return elapse time.
    def get(self):
        if self.halted:
            return self.totalTime
        else:
            return self.totalTime + time.time() - self.startTime
    # halt stopWatch.
    def halt(self):
        self.halted = True
        self.totalTime += time.time() - self.startTime
    # resume stopwatch.
    def resume(self):
        self.halted = False
        self.startTime = time.time()
    # set stopwatch to zero.
    def reset(self):
        self.__init__()


class CancelledError(Exception):
    """The Future was cancelled."""
    pass


class TimeoutError(Exception):
    """The operation exceeded the given deadline."""
    pass


FutureId = namedtuple('FutureId', ['worker', 'rank'])
callbackEntry = namedtuple('callbackEntry', ['func', 'callbackType', 'groupID'])
class Future(object):
    """This class encapsulates an independent future that can be executed in parallel.
    A future can spawn other parallel futures which themselves can recursively spawn
    other futures."""
    rank = itertools.count()
    def __init__(self, parentId, callable, *args, **kargs):
        """Initialize a new Future."""
        self.id = FutureId(scoop.worker, next(Future.rank))
        self.executor = None  # id of executor
        self.parentId = parentId  # id of parent
        self.index = None  # parent index for result
        self.callable = callable  # callable object
        self.args = args  # arguments of callable
        self.kargs = kargs  # key arguments of callable
        self.creationTime = time.ctime()  # future creation time
        self.stopWatch = StopWatch()  # stop watch for measuring time
        self.greenlet = None  # cooperative thread for running future
        self.resultValue = None  # future result
        self.exceptionValue = None  # exception raised by callable
        self.sendResultBack = True
        self.isDone = False
        self.callback = []  # set callback
        self.children = {}  # set children list of the callable (dict for speedier delete)
        # insert future into global dictionary
        scoop._control.futureDict[self.id] = self

    def __lt__(self, other):
        """Order futures by creation time."""
        return self.creationTime < other.creationTime

    def __repr__(self):
        """Convert future to string."""
        try:
            return "{0}:{1}{2}={3}".format(self.id,
                                       self.callable.__name__,
                                       self.args,
                                       self.resultValue)
        except AttributeError:
            return "{0}:{1}{2}={3}".format(self.id,
                                       "partial",
                                       self.args,
                                       self.resultValue)

    def _switch(self, future):
        """Switch greenlet."""
        scoop._control.current = self
        assert self.greenlet is not None, ("No greenlet to switch to:"
                                           "\n{0}".format(self.__dict__))
        return self.greenlet.switch(future)

    def cancel(self):
        """If the call is currently being executed or sent for remote
           execution, then it cannot be cancelled and the method will return
           False, otherwise the call will be cancelled and the method will
           return True."""
        if self in scoop._control.execQueue.movable:
            self.exceptionValue = CancelledError()
            scoop._control.futureDict[self.id]._delete()
            scoop._control.execQueue.remove(self)
            return True
        return False

    def cancelled(self):
        """Returns True if the call was successfully cancelled, False
        otherwise."""
        return isinstance(self.exceptionValue, CancelledError)

    def running(self):
        """Returns True if the call is currently being executed and cannot be
           cancelled."""
        return not self._ended() and self not in scoop._control.execQueue

    def done(self):
        """Returns True if the call was successfully cancelled or finished
           running, False otherwise. This function updates the executionQueue
           so it receives all the awaiting message."""
        # Flush the current future in the local buffer (potential deadlock
        # otherwise)
        try:
            scoop._control.execQueue.remove(self)
            scoop._control.execQueue.socket.sendFuture(self)
        except ValueError as e:
            # Future was not in the local queue, everything is fine
            pass
        # Process buffers
        scoop._control.execQueue.updateQueue()
        return self._ended()


    def _ended(self):
        """True if the call was successfully cancelled or finished running,
           False otherwise. This function does not update the queue."""
        # TODO: Replace every call to _ended() to .isDone
        return self.isDone

    def result(self, timeout=None):
        """Return the value returned by the call. If the call hasn't yet
        completed then this method will wait up to ''timeout'' seconds. More
        information in the :doc:`usage` page. If the call hasn't completed in
        timeout seconds then a TimeoutError will be raised. If timeout is not
        specified or None then there is no limit to the wait time.

        If the future is cancelled before completing then CancelledError will
        be raised.

        If the call raised an exception then this method will raise the same
        exception.

        :returns: The value returned by the callable object."""
        if not self._ended():
            return scoop.futures._join(self)
        if self.exceptionValue is not None:
            raise self.exceptionValue
        return self.resultValue

    def exception(self, timeout=None):
        """Return the exception raised by the call. If the call hasn't yet
        completed then this method will wait up to timeout seconds. More
        information in the :doc:`usage` page. If the call hasn't completed in
        timeout seconds then a TimeoutError will be raised. If timeout is not
        specified or None then there is no limit to the wait time.

        If the future is cancelled before completing then CancelledError will be
        raised.

        If the call completed without raising then None is returned.

        :returns: The exception raised by the call."""
        return self.exceptionValue

    def add_done_callback(self, callable_,
                          inCallbackType=CallbackType.standard,
                          inCallbackGroup=None):
        """Attach a callable to the future that will be called when the future
        is cancelled or finishes running. Callable will be called with the
        future as its only argument.

        Added callables are called in the order that they were added and are
        always called in a thread belonging to the process that added them. If
        the callable raises an Exception then it will be logged and ignored. If
        the callable raises another BaseException then behavior is not defined.

        If the future has already completed or been cancelled then callable will
        be called immediately."""
        self.callback.append(callbackEntry(callable_,
                                           inCallbackType,
                                           inCallbackGroup))

        # If already completed or cancelled, execute it immediately
        if self._ended():
            self.callback[-1].func(self)

    def _execute_callbacks(self, callbackType=CallbackType.standard):
        for callback in self.callback:
            isUniRun = (self.parentId.worker == scoop.worker 
                        and callbackType == CallbackType.universal)
            if isUniRun or callback.callbackType == callbackType:
                try:
                    callback.func(self)
                except:
                    pass

    def _delete(self):
        # TODO: Do we need this?
        if self.id in scoop._control.execQueue.inprogress:
            del scoop._control.execQueue.inprogress[self.id]
        for child in self.children:
            child.exceptionValue = CancelledError()
        scoop._control.delFuture(self)


class FutureQueue(object):
    """This class encapsulates a queue of futures that are pending execution.
    Within this class lies the entry points for future communications."""
    def __init__(self):
        """Initialize queue to empty elements and create a communication
        object."""
        self.movable = deque()
        self.ready = deque()
        self.inprogress = {}
        self.socket = Communicator()
        if scoop.SIZE == 1 and not scoop.CONFIGURATION.get('headless', False):
            self.lowwatermark = float("inf")
            self.highwatermark = float("inf")
        else:
            # TODO: Make it dependent on the network latency
            self.lowwatermark = 0.01
            self.highwatermark = 0.01

    def __iter__(self):
        """Iterates over the selectable (cancellable) elements of the queue."""
        return itertools.chain(self.movable, self.ready)

    def __len__(self):
        """Returns the length of the queue, meaning the sum of it's elements
        lengths."""
        return len(self.movable) + len(self.ready)

    def timelen(self, queue_):
        stats = scoop._control.execStats
        times = Counter(hash(f.callable) for f in queue_)
        return sum(stats[f].mean() * occur for f, occur in times.items())

    def append(self, future):
        """Append a future to the queue."""
        if future._ended() and future.index is None:
            self.inprogress[future.id] = future
        elif future._ended() and future.index is not None:
            self.ready.append(future)
        elif future.greenlet is not None:
            self.inprogress.append(future)
        else:
            self.movable.append(future)

            # Send the oldest future in the movable deque until under the hwm
            over_hwm = self.timelen(self.movable) > self.highwatermark
            while over_hwm and len(self.movable) > 1:
                sending_future = self.movable.popleft()
                if sending_future.id.worker != scoop.worker:
                    sending_future._delete()
                self.socket.sendFuture(sending_future)

    def pop(self):
        """Pop the next future from the queue;
        in progress futures have priority over those that have not yet started;
        higher level futures have priority over lower level ones; """
        self.updateQueue()

        # If our buffer is underflowing, request more Futures
        if self.timelen(self) < self.lowwatermark:
            self.requestFuture()

        # If an unmovable Future is ready to be executed, return it
        if len(self.ready) != 0:
            return self.ready.popleft()

        # Then, use Futures in the movable queue
        elif len(self.movable) != 0:
            return self.movable.popleft()
        else:
            # Otherwise, block until a new task arrives
            while len(self) == 0:
                # Block until message arrives
                self.socket._poll(-1)
                self.updateQueue()
            if len(self.ready) != 0:
                return self.ready.popleft()
            elif len(self.movable) != 0:
                return self.movable.popleft()

    def flush(self):
        """Empty the local queue and send its elements to be executed remotely.
        """
        for elem in self:
            if elem.id.worker != scoop.worker:
                elem._delete()
            self.socket.sendFuture(elem)
        self.ready.clear()
        self.movable.clear()

    def requestFuture(self):
        """Request futures from the broker"""
        self.socket.sendRequest()

    def updateQueue(self):
        """Process inbound communication buffer.
        Updates the local queue with elements from the broker."""
        for future in self.socket.recvFuture():
            if future._ended():
                # If the answer is coming back, update its entry
                try:
                    thisFuture = scoop._control.futureDict[future.id]
                except KeyError:
                    # Already received?
                    scoop.logger.warn('{0}: Received an unexpected future: '
                                      '{1}'.format(scoop.worker, future.id))
                    continue
                thisFuture.resultValue = future.resultValue
                thisFuture.exceptionValue = future.exceptionValue
                thisFuture.executor = future.executor
                thisFuture.isDone = future.isDone
                # Execute standard callbacks here (on parent)
                thisFuture._execute_callbacks(CallbackType.standard)
                self.append(thisFuture)
                future._delete()
            elif future.id not in scoop._control.futureDict:
                scoop._control.futureDict[future.id] = future
                self.append(scoop._control.futureDict[future.id])
            else:
                self.append(scoop._control.futureDict[future.id])
        to_remove = []
        for future in self.inprogress.values():
            if future.index is not None:
                self.ready.append(future)
                to_remove.append(future)
        for future in to_remove:
            del self.inprogress[future.id]

    def remove(self, future):
        """Remove a future from the queue. The future must be cancellable or
        this method will raise a ValueError."""
        self.movable.remove(future)

    def sendResult(self, future):
        """Send back results to broker for distribution to parent task."""
        # Greenlets cannot be pickled
        future.greenlet = None
        assert future._ended(), "The results are not valid"
        self.socket.sendResult(future)

    def shutdown(self):
        """Shutdown the ressources used by the queue"""
        self.socket.shutdown()
