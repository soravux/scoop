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
from collections import namedtuple, deque
import scoop
from .comm import ZMQCommunicator
from .comm import Shutdown
import control
import time
import greenlet


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
            return self.totalTime + time.time()-self.startTime
    # halt stopWatch.
    def halt(self):
        self.halted = True
        self.totalTime += time.time()-self.startTime
    # resume stopwatch.
    def resume(self):
        self.halted = False
        self.startTime = time.time()
    # set stopwatch to zero.
    def reset(self):
        self.__init__()


TaskId = namedtuple('TaskId', ['worker', 'rank'])
class Task(object):
    """This class encapsulates and independent task that can be executed in parallel.
    A task can spawn other parallel tasks which themselves can recursively spawn
    other tasks."""
    
    def __init__(self, parentId, callable, *args, **kargs):
        """Initialize a new task."""
        self.id = TaskId(control.worker, control.rank); control.rank += 1
        self.parentId = parentId          # id of parent
        self.index = None                 # parent index for result
        self.callable = callable          # callable object
        self.args = args                  # arguments of callable
        self.kargs = kargs                # key arguments of callable
        self.creationTime = time.ctime()  # task creation time
        self.stopWatch = StopWatch()      # stop watch for measuring time
        self.greenlet = None              # cooperative thread for running task 
        self.result = None                # task result
        self.callback = None              # set callback
        # insert task into global dictionary
        control.task_dict[self.id] = self

    def __lt__(self, other):
        """Order tasks by creation time."""
        return self.creationTime < other.creationTime
    
    def __str__(self):
        """Convert task to string."""
        return "{0}[{3}] = {1}{5}={2}, p={4}".format(self.id,
                                                     self.callable,
                                                     self.result,
                                                     self.index,
                                                     self.parentId,
                                                     self.args)
   
    def __repr__(self):
        return "{0}[{1}] = {2}, p = {3}".format(self.id,self.index, self.result, self.parentId)
    
    def switch(self, task):
        """Switch greenlet."""
        control.current = self
        assert self.greenlet != None, "No greenlet to switch to:\n%s" % self.__dict__
        return self.greenlet.switch(task)
    
    # The following methods are added to be compliant with PEP3148
    def cancel(self):
        """Attempt to cancel the call. 
        
        :returns: If the call is currently being executed then it cannot
            be cancelled and the method will return False, otherwise
            the call will be cancelled and the method will return True."""
        # TODO
        pass

    def cancelled(self):
        """Returns a status flag of the process.
        
        :returns: True if the call was successfully cancelled, else
            otherwise."""
        # TODO
        pass

    def running(self):
        """Returns a status flag of the process.
        
        :returns: True if the call is currently being executed and cannot be
            cancelled."""
        # TODO
        pass
        
    def done(self):
        """Returns a status flag of the process.
        
        :returns: True if the call was successfully cancelled or finished
            running."""
        # TODO
        pass

    def result(self, timeout=None):
        """Return the value returned by the call. If the call hasn't yet
        completed then this method will wait up to ''timeout'' seconds. If the
        call hasn't completed in timeout seconds then a TimeoutError will be
        raised. If timeout is not specified or None then there is no limit to
        the wait time.
        
        If the future is cancelled before completing then CancelledError will
        be raised.

        If the call raised then this method will raise the same exception.
        
        :returns: The value returned by the call."""
        # TODO
        return self.result

    def exception(self, timeout=None):
        """Return the exception raised by the call. If the call hasn't yet
        completed then this method will wait up to timeout seconds. If the call
        hasn't completed in timeout seconds then a TimeoutError will be raised.
        If timeout is not specified or None then there is no limit to the wait
        time.

        If the future is cancelled before completing then CancelledError will be
        raised.

        If the call completed without raising then None is returned.
        
        :returns: The exception raised by the call."""
        # TODO
        pass

    def add_done_callback(self, callable):
        """Attaches a callable to the future that will be called when the future
        is cancelled or finishes running. Callable will be called with the
        future as its only argument.

        Added callables are called in the order that they were added and are
        always called in a thread belonging to the process that added them. If
        the callable raises an Exception then it will be logged and ignored. If
        the callable raises another BaseException then behavior is not defined.

        If the future has already completed or been cancelled then callable will
        be called immediately."""
        # TODO
        pass


class TaskQueue(object):
    """This class encapsulates a queue of tasks that are pending execution.
    Within this class lies the entry points for task communications."""
    def __init__(self):
        """initialize queue to empty elements and create a communication
        object."""
        self.movable = deque()
        self.ready = deque()
        self.inprogress = deque()
        self.socket = ZMQCommunicator()
        self.lowwatermark  = 5
        self.highwatermark = 20

    def __len__(self):
        """ returns the length of the queue, meaning the sum of it's
        elements lengths."""
        return len(self.movable) + len(self.ready)
    
    def append(self, task):
        """ append a task to the queue."""
        if task.result != None and task.index == None:
            self.inprogress.append(task)
        elif task.result != None and task.index != None:
            self.ready.append(task)
        elif task.greenlet != None:
            self.inprogress.append(task)
        elif len(self) > self.highwatermark:
            self.socket.sendTask(task)
        else:
            self.movable.append(task)
        
    def pop(self):
        """pop the next task from the queue; 
        in progress tasks have priority over those that have not yet started;
        higher level tasks have priority over lower level ones; """
        self.updateQueue()
        if len(self) < self.lowwatermark:
            self.requestTask()
        if len(self.ready) != 0:
            return self.ready.pop()
        elif len(self.movable) != 0:
            return self.movable.pop()
        else:
            while len(self) == 0:
                # Block until message arrives
                self.socket._poll(-1)
                self.updateQueue()
            if len(self.ready) != 0:
                return self.ready.pop()
            elif len(self.movable) != 0:
                return self.movable.pop()

    def requestTask(self):
        for a in range(len(self), self.lowwatermark + 1):
            self.socket.sendRequest()
    
    def updateQueue(self):
        """updates the local queue with elements from the broker."""
        to_remove = []
        for task in self.inprogress:
            if task.index != None:
                self.ready.append(task)
                to_remove.append(task)
        for task in to_remove:
            self.inprogress.remove(task)        
        for task in self.socket.recvTask():
            if task.id in control.task_dict:
                control.task_dict[task.id].result = task.result
            else:
                control.task_dict[task.id] = task
            task = control.task_dict[task.id]
            self.append(task)
    
    def select(self, duration):
        """return a list of movable tasks that have an estimated total runtime
        of at most "duration" seconds."""
        pass

    def sendResult(self, task):
        task.greenlet = None  # greenlets cannot be pickled
        assert task.result != None, "The results are not valid"
        self.socket.sendResult(task)
        

class Future(object): pass