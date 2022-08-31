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
from scoop._comm.scoopmessages import *

# Backporting collection features
if sys.version_info < (2, 7):
    from scoop.backports.newCollections import Counter
else:
    from collections import Counter


POLLING_TIME = 2000


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


class UnrecognizedFuture(Exception):
    """Some Operation Involved an invalid/unrecognized future"""
    pass


callbackEntry = namedtuple('callbackEntry', ['func', 'callbackType', 'groupID'])
class Future(object):
    """This class encapsulates an independent future that can be executed in parallel.
    A future can spawn other parallel futures which themselves can recursively spawn
    other futures."""
    rank = itertools.count()
    def __init__(self, parentId, callable, *args, **kargs):
        """Initialize a new Future."""
        self.id = (scoop.worker, next(Future.rank))
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
        self.isReady = False  # Once this is true, the future is out of our hands
        self.callback = []  # set callback
        self.children = {}  # set children list of the callable (dict for speedier delete)
        # insert future into global dictionary
        scoop._control.futureDict[self.id] = self

    def __lt__(self, other):
        """Order futures by creation time."""
        return self.creationTime < other.creationTime

    def __eq__(self, other):
        # This uses he fact that id's are unique
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        """Convert future to string."""
        try:
            return "{0}:{1}{2}{3}={4}".format(
                self.id,
                self.callable.__name__,
                self.args,
                self.kargs,
                self.resultValue,
            )
        except AttributeError:
            return "{0}:{1}{2}{3}={4}".format(
                self.id,
                "partial",
                self.args,
                self.kargs,
                self.resultValue,
            )

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
            for child in self.children:
                child.exceptionValue = CancelledError()
            scoop._control.delFuture(self)
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
            isUniRun = (self.parentId[0] == scoop.worker 
                        and callbackType == CallbackType.universal)
            if isUniRun or callback.callbackType == callbackType:
                try:
                    callback.func(self)
                except:
                    pass


class FutureQueue(object):
    """This class encapsulates a queue of futures that are pending execution.
    Within this class lies the entry points for future communications."""
    def __init__(self):
        """Initialize queue to empty elements and create a communication
        object."""
        self.movable = deque()
        self.ready = deque()
        self.inprogress = set()
        self.socket = Communicator()
        self.request_in_process = False
        if scoop.SIZE == 1 and not scoop.CONFIGURATION.get('headless', False):
            self.lowwatermark = float("inf")
            self.highwatermark = float("inf")
        else:
            # TODO: Make it dependent on the network latency
            self.lowwatermark = 0.01
            self.highwatermark = 0.01

    def __del__(self):
        """Destructor. Ensures Communicator is correctly discarted."""
        self.shutdown()

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
        return sum(stats[f].median() * occur for f, occur in times.items())

    def append_ready(self, future):
        """
        This appends a ready future to the queue.

        NOTE: A Future is ready iff it has completed execution and been
        processed by the worker that generated it
        """
        if future.isReady:
            self.ready.append(future)
        else:
            raise ValueError(
                ("The future id {} has not been assimilated"
                 " before adding, on worker: {}").format(future.id,
                                                         scoop.worker))

    def append_init(self, future):
        """
        This appends a movable future to the queue FOR THE FIRST TIME.

        NOTE: This is different from append_movable in that all the futures
        are not actually appended but are sent to the broker.
        """
        if future.greenlet is None and not future.isDone and future.id[0] == scoop.worker:
            self.socket.sendFuture(future)
        else:
            raise ValueError((
                "The future id {} being added to queue initially is not "
                " movable before adding, on worker: {}").format(future.id,
                                                                scoop.worker))

    def append_movable(self, future):
        """
        This appends a movable future to the queue.

        NOTE: A Future is movable if it hasn't yet begun execution. This is
        characterized by the lack of a greenlet and not having completed. Also note
        that this function is only called when appending a future retrieved from the
        broker. to append a newly spawned future, use `FutureQueue.append_init`
        """
        if future.greenlet is None and not future.isDone:
            self.movable.append(future)
            assert len(self.movable) == 1, "movable size isnt adding up"
        else:
            raise ValueError((
                "The future id {} being added to movable queue is not "
                " movable before adding, on worker: {}").format(future.id,
                                                                scoop.worker))

    def pop(self):
        """Pop the next future from the queue;
        ready futures have priority over those that have not yet started;

        It is ASSUMED that any queue popped from the movable queue, identifiable
        by _ended() == False (Note that self.inprogress is never 'popped') is
        going to be executed and hence will be added to the inprogress set of
        execQueue."""

        # Check if queue is empty
        while len(self) == 0:
            # If so, Block until message arrives. Only send future request once (to
            # ensure FCFS). This has the following potential issue. If a node
            # disconnects and reconnects and is considered by the broker to be lost,
            # there is a possibility that it has been removed from the brokers list
            # of assignable workers, in which case, this worker will forever be
            # stuck in this loop. However, this is a problem that is expected to
            # NEVER happen and therefore we leave it be. Currently, I have added
            # some code that can be used to protect against this (see
            # FutureQueue.checkRequestStatus, REQUEST_STATUS_REQUEST and related)
            if not self.request_in_process:
                self.requestFuture()

            self.socket._poll(POLLING_TIME)
            self.updateQueue()
        if len(self.ready) != 0:
            return self.ready.popleft()
        elif len(self.movable) != 0:
            self.inprogress.add(self.movable[0])
            return self.movable.popleft()

    def flush(self):
        """Empty the local queue and send its elements to be executed remotely.
        """
        for elem in self:
            if elem.id[0] != scoop.worker:
                scoop._control.delFuture(elem)
            self.socket.sendFuture(elem)
        self.ready.clear()
        self.movable.clear()

    def requestFuture(self):
        """Request futures from the broker"""
        self.socket.sendRequest()
        self.request_in_process = True

    def updateQueue(self):
        """Process inbound communication buffer.
        Updates the local queue with elements from the broker.

        Note that the broker only sends either non-executed (movable)
        futures, or completed futures"""
        for incoming_msg in self.socket.recvIncoming():
            incoming_msg_categ = incoming_msg[0]
            incoming_msg_value = incoming_msg[1]

            if incoming_msg_categ == REPLY:
                future = incoming_msg_value
                # If the answer is coming back, update its entry
                try:
                    thisFuture = scoop._control.futureDict[future.id]
                except KeyError:
                    # Already received?
                    scoop.logger.warn('{0}: Received an unexpected future: '
                                      '{1}'.format(scoop.worker, future.id))
                    return
                thisFuture.resultValue = future.resultValue
                thisFuture.exceptionValue = future.exceptionValue
                thisFuture.executor = future.executor
                thisFuture.isDone = future.isDone
                self.finalizeReturnedFuture(thisFuture)
            elif incoming_msg_categ == TASK:
                future = incoming_msg_value
                if future.id not in scoop._control.futureDict:
                    # This is the case where the worker is executing a remotely
                    # generated future
                    scoop._control.futureDict[future.id] = future
                    self.append_movable(scoop._control.futureDict[future.id])
                else:
                    # This is the case where the worker is executing a locally
                    # generated future
                    self.append_movable(scoop._control.futureDict[future.id])
                if len(self.movable) > 0:
                    # This means that a future has been returned corresponding to the
                    # future request
                    self.request_in_process = False
            elif incoming_msg_categ == RESEND_FUTURE:
                future_id = incoming_msg_value
                try:
                    scoop.logger.warning(
                        "Lost track of future {0}. Resending it..."
                        "".format(scoop._control.futureDict[future_id])
                    )
                    self.socket.sendFuture(scoop._control.futureDict[future_id])
                except KeyError:
                    # Future was received and processed meanwhile
                    scoop.logger.warning(
                        "Asked to resend unexpected future id {0}. future not found"
                        " (likely received and processed in the meanwhile)"
                        "".format(future_id)
                    )
            else:
                assert False, "Unrecognized incoming message"

    def finalizeReturnedFuture(self, future):
        """Finalize a future that was generated here and executed remotely.
        """
        if not (future.executor[0] != scoop.worker == future.id[0]
                and future.isDone):
            raise UnrecognizedFuture(("The future ID {0} was not executed"
                                      " remotely and returned, worker: {1}")
                                     .format(future.id, scoop.worker))
        # Execute standard callbacks here (on parent)
        future._execute_callbacks(CallbackType.standard)
        scoop._control.delFuture(future)
        future.isReady = True
        self.append_ready(future)

    def finalizeFuture(self, future):
        """Finalize an ended future, this does the following:
        
        1.  The future is checked to see if it was inprogress or not on this thread,
        2.  All references to the future are removed
        3.  The future is added to the ready queue of the parent process

        NOTE: After this function, do not continue to process this future, pick
        a new one from the queue
        """
        if not (future in self.inprogress and future.isDone):
            raise UnrecognizedFuture(
                ("The future ID {0} was not in progress on worker"
                 " {1}, finalize is undefined ").format(future.id, scoop.worker))

        scoop._control.delFuture(future)
        self.inprogress.remove(future)

        if future.id[0] == scoop.worker:
            future.isReady = True
            self.append_ready(future)
        else:
            self.sendResult(future)
            
    def sendReadyStatus(self, future):
        """This should only be called after the future has been finalized on the worker.
        """
        self.socket.sendReadyStatus(future)

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

        if scoop:
            if scoop.DEBUG:
                from scoop import _debug
                _debug.writeWorkerDebug(
                    scoop._control.debug_stats,
                    scoop._control.QueueLength,
                )