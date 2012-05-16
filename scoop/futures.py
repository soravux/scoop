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
from .control import runController
from .types import Task
import greenlet
import scoop

# This is the greenlet for running the controller logic.
_controller = None

def startup(rootTask, *args, **kargs):
    """This function initializes the SCOOP environment.
    
    :param rootTask: Any callable object (function or class object with __call__
        method); this object will be called once and allows the use of parallel
        calls inside this object.
    :param args: A tuple of positional arguments that will be passed to the 
        callable object. 
    :param kargs: A tuple of iterable objects; each will be zipped to form an
        iterable of arguments tuples that will be passed to the callable object
        as a separate task. 
        
    :returns: The result of the root task.
    
    Be sure to launch your root task using this method."""
    global _controller
    _controller = greenlet.greenlet(runController)
    try:
        result = _controller.switch(rootTask, *args, **kargs)
    except scoop.socket.Shutdown:
        return None
    return result
    
def shutdown(): pass

def map(callable, *iterables, **kargs):
    """This function is similar to the built-in map function, but each of its 
    iteration will spawn a separate independent parallel task that will run 
    either locally or remotely as `callable(*args, **kargs)`.
    
    :param callable: Any callable object (function or class object with __call__
        method); this object will be called to execute each task. 
    :param iterables: A tuple of iterable objects; each will be zipped
        to form an iterable of arguments tuples that will be passed to the
        callable object as a separate task. 
    :param kargs: A dictionary of additional keyword arguments that will be 
        passed to the callable object. 
    :returns: A list of task objects, each corresponding to an iteration of map.
    
    On return, the tasks are pending execution locally, but may also be
    transfered remotely depending on global load. Execution may be carried on
    with any further computations. To retrieve the map results, you need to
    either wait for or join with the spawned tasks. See functions waitAny,
    waitAll, or joinAll. Alternatively, You may also use functions mapWait or
    mapJoin that will wait or join before returning."""
    childrenList = []
    for args in zip(*iterables):
        childrenList.append(submit(callable, *args, **kargs))
    return childrenList

def mapJoin(callable, *iterables, **kargs):
    """This function is a helper function that simply calls joinAll on the 
    result of map. It returns with a list of the map results, one for every 
    iteration of the map.
    
    :param callable: Any callable object (function or class object with __call__
        method); this object will be called to execute each task. 
    :param iterables: A tuple of iterable objects; each will be zipped
        to form an iterable of arguments tuples that will be passed to the
        callable object as a separate task. 
    :param kargs: A dictionary of additional keyword arguments that will be 
        passed to the callable object. 
    :returns: A list of map results, each corresponding to one map iteration."""
    return joinAll(*map(callable, *iterables, **kargs))

def mapWait(callable, *iterables, **kargs):
    """This function is a helper function that simply calls waitAll on the 
    result of map. It returns with a generator function for the map results, 
    one result for every iteration of the map.
    
    :param callable: Any callable object (function or class object with __call__
        method); this object will be called to execute the tasks. 
    :param iterables: A tuple of iterable objects; each will be zipped
        to form an iterable of arguments tuples that will be passed to the
        callable object as a separate task. 
    :param kargs: A dictionary of additional keyword arguments that will be 
        passed to the callable object. 
    :returns: A generator of map results, each corresponding to one map 
        iteration."""
    return waitAll(*map(callable, *iterables, **kargs))

def submit(callable, *args, **kargs):
    """This function is for submitting an independent parallel task that will 
    either run locally or remotely as `callable(*args, **kargs)`.
    
    :param callable: Any callable object (function or class object with __call__
        method); this object will be called to execute the task. 
    :param args: A tuple of positional arguments that will be passed to the 
        callable object. 
    :param kargs: A dictionary of additional keyword arguments that will be 
        passed to the callable abject. 
    :returns: A future object for retrieving the task result.
    
    On return, the task is pending execution locally, but may also be transfered
    remotely depending on load. or on remote distributed workers. You may carry
    on with any further computations while the task completes. To retrieve the
    task result, you need to either wait for or join with the parallel task. See
    functions waitAny or join."""
    child = Task(Task.current.id, callable, *args, **kargs)
    Task.execQueue.append(child)
    return child

def waitAny(*children):
    """This function is for waiting on any child task created by the calling 
    task.
    
    :param children: A tuple of children task objects spawned by the calling 
        task.
    :return: A generator function that iterates on (index, result) tuples.
    
    The generator produces two-element tuples. The first element is the index of
    a result, and the second is the result itself. The index corresponds to the
    index of the task in the children argument. Tuples are generated in a non
    deterministic order that depends on the particular parallel execution of the
    tasks. The generator returns a tuple as soon as one becomes available. Any
    number of children tasks can be specified, for example just one, all of
    them, or any subset of created tasks, but they must have been spawned by the 
    calling task (using map or submit). See also waitAll for an alternative 
    option."""
    n = len(children)
    # check for available results and index those unavailable
    for index, task in enumerate(children):
        if task.result:
            yield task.result
            n -= 1
        else:
            task.index = index
    task = Task.current
    while n > 0:
        # wait for remaining results; switch to controller
        task.stopWatch.halt()
        result = _controller.switch(task)
        task.stopWatch.resume()
        yield result
        n -= 1

def waitAll(*children):
    """This function is for waiting on all child tasks specified by a tuple of 
    previously created task (using map or submit).
    
    :param children: A tuple of children task objects spawned by the calling 
        task.
    :return: A generator function that iterates on task results.
    
    The generator produces results in the order that they are specified by
    the children argument. Because task are executed in a non deterministic 
    order, the generator may have to wait for the last result to become 
    available before it can produce an output. See waitAny for an alternative 
    option."""
    for index, task in enumerate(children):
        #yield waitAny(task).next()
        for result in waitAny(task):
            yield result
        
def join(child):
    """This function is for joining the current task with one of its child 
    task.
    
    :param child: A child task object spawned by the calling task.
    :return: The result of the child task.
    
    Only one task can be specified. The function returns a single corresponding 
    result as soon as it becomes available."""
    #return waitAny(child).next()
    for result in waitAny(child):
        return result


def joinAll(*children):
    """This function is for joining the current task with all of the children 
    tasks specified in a tuple.
    
    :param children: A tuple of children task objects spawned by the calling 
        task.
    :return: A list of corresponding results for the children tasks.
    
    This function will wait for the completion of all specified child tasks 
    before returning to the caller."""
    return [result for result in waitAll(*children)]
