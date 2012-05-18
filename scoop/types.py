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
from collections import namedtuple
import scoop
from .socket import MySocket
from .socket import Shutdown
import time
import greenlet
from collections import deque


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


# This class encapsulates a queue of tasks that are pending execution. Within
# this class lies the entry points for task communications.
class TaskQueue(object):
    # initialize queue to empty elements and create a communication object.
    def __init__(self):
        self.movable = deque()
        self.ready = deque()
        self.inprogress = deque()
        self.socket = MySocket()
        self.lowwatermark  = 5
        self.highwatermark = 20

    # returns the length of the queue, meaning the sum of it's elements lengths.
    def __len__(self):
        return len(self.movable) + len(self.ready)
    
    # append a task to the queue.
    def append(self, task):
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
        
    # pop the next task from the queue; 
    # in progress tasks have priority over those that have not yet started;
    # higher level tasks have priority over lower level ones; 
    def pop(self):
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
    
    # updates the local queue with elements from 
    def updateQueue(self):
        to_remove = []
        for task in self.inprogress:
            if task.index != None:
                self.ready.append(task)
                to_remove.append(task)
                #self.inprogress.remove(task)
        for task in to_remove:
            self.inprogress.remove(task)        
        for task in self.socket.recvTask():
            if task.id in Task.dict:
                Task.dict[task.id].result = task.result
            else:
                Task.dict[task.id] = task
            task = Task.dict[task.id]
            self.append(task)
    
    # return a list of movable tasks that have an estimated total runtime
    # of at most "duration" seconds.
    def select(self, duration): pass

    def sendResult(self, task):
        task.greenlet = None  # greenlets cannot be pickled
        assert task.result != None, "The results are not valid"
        self.socket.sendResult(task)


# This class encapsulates and independent task that can be executed in parallel.
# A task can spawn other parallel tasks which themselves can recursively spawn
# other tasks. 
class Task(object):
    worker = (scoop.WORKER_NAME, scoop.BROKER_NAME) # worker task id
    rank = 0                                        # rank id for next task
    is_origin = scoop.IS_ORIGIN                     # is the worker the origin?
    current = None                                  # task currently running in greenlet
    dict = {}                                       # dictionary of existing tasks
    execQueue = TaskQueue()                         # queue of tasks pending execution
    
    # initialize task.
    def __init__(self, parentId, callable, *args, **kargs):
        self.id = TaskId(Task.worker, Task.rank); Task.rank += 1
        self.parentId = parentId          # id of parent
        self.index = None                 # parent index for result
        self.callable = callable          # callable object
        self.args = args                  # arguments of callable
        self.kargs = kargs                # key arguments of callable
        self.creationTime = time.ctime()  # task creation time
        self.stopWatch = StopWatch()      # stop watch for measuring time
        self.greenlet = None              # cooperative thread for running task 
        self.result = None                # task result
        # insert task into global dictionary
        Task.dict[self.id] = self

    # order tasks by creation time.
    def __lt__(self, other):
        return self.creationTime < other.creationTime
    
    # convert task to string.
    def __str__(self):
        return "{0}[{3}] = {1}{5}={2}, p={4}".format(self.id,
                                                     self.callable,
                                                     self.result,
                                                     self.index,
                                                     self.parentId,
                                                     self.args)
   
    def __repr__(self):
        return "{0}[{1}] = {2}, p = {3}".format(self.id,self.index, self.result, self.parentId)
    
    # switch greenlet.
    def switch(self, task):
        Task.current = self
        assert self.greenlet != None, "No greenlet to switch to:\n%s" % self.__dict__
        return self.greenlet.switch(task)
    
    # shutdown the task and it's children
    def shutdown(self): pass


class Future(object): pass
