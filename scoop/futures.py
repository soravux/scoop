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
import os
from inspect import ismethod
from collections import namedtuple, Iterable
from functools import partial, reduce
import itertools
import copy
import time

import scoop
from ._types import Future, CallbackType
from . import _control as control
from .fallbacks import (
    ensureScoopStartedProperlyMapFallback,
    ensureScoopStartedProperly,
    NotStartedProperly
)


# Constants stated by PEP 3148 (http://www.python.org/dev/peps/pep-3148/#module-functions)
FIRST_COMPLETED = 'FIRST_COMPLETED'
FIRST_EXCEPTION = 'FIRST_EXCEPTION'
ALL_COMPLETED = 'ALL_COMPLETED'
_AS_COMPLETED = '_AS_COMPLETED'

# This is the greenlet for running the controller logic.
_controller = None
callbackGroupID = itertools.count()


def _startup(rootFuture, *args, **kargs):
    """Initializes the SCOOP environment.

    :param rootFuture: Any callable object (function or class object with *__call__*
        method); this object will be called once and allows the use of parallel
        calls inside this object.
    :param args: A tuple of positional arguments that will be passed to the
        callable object.
    :param kargs: A dictionary of additional keyword arguments that will be
        passed to the callable object.

    :returns: The result of the root Future.

    Be sure to launch your root Future using this method."""
    import greenlet
    global _controller
    _controller = greenlet.greenlet(control.runController)
    try:
        result = _controller.switch(rootFuture, *args, **kargs)
    except scoop._comm.Shutdown:
        result = None
        control.execQueue.shutdown()
    if scoop.DEBUG:
        from scoop import _debug
        _debug.writeWorkerDebug(control.debug_stats,
                                control.QueueLength)
    return result


def _mapFuture(callable_, *iterables):
    """Similar to the built-in map function, but each of its
    iteration will spawn a separate independent parallel Future that will run
    either locally or remotely as `callable(*args)`.

    :param callable: Any callable object (function or class object with *__call__*
        method); this object will be called to execute each Future.
    :param iterables: A tuple of iterable objects; each will be zipped
        to form an iterable of arguments tuples that will be passed to the
        callable object as a separate Future.

    :returns: A list of Future objects, each corresponding to an iteration of
        map.

    On return, the Futures are pending execution locally, but may also be
    transfered remotely depending on global load. Execution may be carried on
    with any further computations. To retrieve the map results, you need to
    either wait for or join with the spawned Futures. See functions waitAny,
    waitAll, or joinAll. Alternatively, You may also use functions mapWait or
    mapJoin that will wait or join before returning."""
    childrenList = []
    for args in zip(*iterables):
        childrenList.append(submit(callable_, *args))
    return childrenList

def _mapGenerator(futures):
    """Generator function that iterates through the results in-order."""
    for future in _waitAll(*futures):
        yield future.resultValue


@ensureScoopStartedProperlyMapFallback
def map(func, *iterables, **kwargs):
    """map(func, *iterables)
    Equivalent to
    `map(func, \*iterables, ...)
    <http://docs.python.org/library/functions.html#map>`_
    but *func* is executed asynchronously
    and several calls to func may be made concurrently. This non-blocking call
    returns an iterator which raises a TimeoutError if *__next__()* is called
    and the result isn't available after timeout seconds from the original call
    to *map()*. If timeout is not specified or None then there is no limit to
    the wait time. If a call raises an exception then that exception will be
    raised when its value is retrieved from the iterator.

    :param func: Any picklable callable object (function or class object with
        *__call__* method); this object will be called to execute the Futures.
        The callable must return a value.
    :param iterables: Iterable objects; each will be zipped to form an iterable
        of arguments tuples that will be passed to the callable object as a
        separate Future.
    :param timeout: The maximum number of seconds to wait. If None, then there
        is no limit on the wait time.

    :returns: A generator of map results, each corresponding to one map
        iteration."""
    # TODO: Handle timeout
    futures = _mapFuture(func, *iterables)
    return _mapGenerator(futures)


def map_as_completed(func, *iterables, **kwargs):
    """map_as_completed(func, *iterables)
    Equivalent to map, but the results are returned as soon as they are made
    available.

    :param func: Any picklable callable object (function or class object with
        *__call__* method); this object will be called to execute the Futures.
        The callable must return a value.
    :param iterables: Iterable objects; each will be zipped to form an iterable
        of arguments tuples that will be passed to the callable object as a
        separate Future.
    :param timeout: The maximum number of seconds to wait. If None, then there
        is no limit on the wait time.

    :returns: A generator of map results, each corresponding to one map
        iteration."""
    # TODO: Handle timeout
    for future in as_completed(_mapFuture(func, *iterables)):
        yield future.resultValue


def _recursiveReduce(mapFunc, reductionFunc, scan, *iterables):
    """Generates the recursive reduction tree. Used by mapReduce."""
    if iterables:
        half = min(len(x) // 2 for x in iterables)
        data_left = [list(x)[:half] for x in iterables]
        data_right = [list(x)[half:] for x in iterables]
    else:
        data_left = data_right = [[]]

    # Submit the left and right parts of the reduction
    out_futures = [None, None]
    out_results = [None, None]
    for index, data in enumerate([data_left, data_right]):
        if any(len(x) <= 1 for x in data):
            out_results[index] = mapFunc(*list(zip(*data))[0])
        else:
            out_futures[index] = submit(
                _recursiveReduce,
                mapFunc,
                reductionFunc,
                scan,
                *data
            )

    # Wait for the results
    for index, future in enumerate(out_futures):
        if future:
            out_results[index] = future.result()

    # Apply a scan if needed
    if scan:
        last_results = copy.copy(out_results)
        if type(out_results[0]) is not list:
            out_results[0] = [out_results[0]]
        else:
            last_results[0] = out_results[0][-1]
        if type(out_results[1]) is list:
            out_results[0].extend(out_results[1][:-1])
            last_results[1] = out_results[1][-1]
        out_results[0].append(reductionFunc(*last_results))
        return out_results[0]

    return reductionFunc(*out_results)


@ensureScoopStartedProperly
def mapScan(mapFunc, reductionFunc, *iterables, **kwargs):
    """Exectues the :meth:`~scoop.futures.map` function and then applies a
    reduction function to its result while keeping intermediate reduction
    values. This is a blocking call.

    :param mapFunc: Any picklable callable object (function or class object with
        *__call__* method); this object will be called to execute the Futures.
        The callable must return a value.
    :param reductionFunc: Any picklable callable object (function or class object
        with *__call__* method); this object will be called to reduce pairs of
        Futures results. The callable must support two parameters and return a
        single value.
    :param iterables: Iterable objects; each will be zipped to form an iterable
        of arguments tuples that will be passed to the mapFunc object as a
        separate Future.
    :param timeout: The maximum number of seconds to wait. If None, then there
        is no limit on the wait time.

    :returns: Every return value of the reduction function applied to every
              mapped data sequentially ordered."""
    return submit(
        _recursiveReduce,
        mapFunc,
        reductionFunc,
        True,
        *iterables
    ).result()


@ensureScoopStartedProperly
def mapReduce(mapFunc, reductionFunc, *iterables, **kwargs):
    """Exectues the :meth:`~scoop.futures.map` function and then applies a
    reduction function to its result. The reduction function will cumulatively
    merge the results of the map function in order to get a single final value.
    This call is blocking.

    :param mapFunc: Any picklable callable object (function or class object
        with *__call__* method); this object will be called to execute the
        Futures. The callable must return a value.
    :param reductionFunc: Any picklable callable object (function or class
        object with *__call__* method); this object will be called to reduce
        pairs of Futures results. The callable must support two parameters and
        return a single value.
    :param iterables: Iterable objects; each will be zipped to form an iterable
        of arguments tuples that will be passed to the callable object as a
        separate Future.
    :param timeout: The maximum number of seconds to wait. If None, then there
        is no limit on the wait time.

    :returns: A single value."""
    return submit(
        _recursiveReduce,
        mapFunc,
        reductionFunc,
        False,
        *iterables
    ).result()


def _createFuture(func, *args):
    """Helper function to create a future."""
    assert callable(func), (
        "The provided func parameter is not a callable."
    )

    # If function is a lambda or class method, share it (or its parent object)
    # beforehand
    lambdaType = type(lambda: None)
    funcIsLambda = isinstance(func, lambdaType) and func.__name__ == '<lambda>'
    # Determine if function is a method. Methods derived from external
    # languages such as C++ aren't detected by ismethod.
    funcIsMethod = ismethod(func)
    if funcIsLambda or funcIsMethod:
        from .shared import SharedElementEncapsulation
        func = SharedElementEncapsulation(func)

    return Future(control.current.id, func, *args)

@ensureScoopStartedProperly
def submit(func, *args):
    """Submit an independent asynchronous :class:`~scoop._types.Future` that will
    either run locally or remotely as `func(*args)`.

    :param func: Any picklable callable object (function or class object with
        *__call__* method); this object will be called to execute the Future.
        The callable must return a value.
    :param args: A tuple of positional arguments that will be passed to the
        func object.

    :returns: A future object for retrieving the Future result.

    On return, the Future can be pending execution locally but may also be
    transfered remotely depending on load or on remote distributed workers. You
    may carry on with any further computations while the Future completes.
    Result retrieval is made via the :meth:`~scoop._types.Future.result`
    function on the Future."""
    child = _createFuture(func, *args)

    control.futureDict[control.current.id].children[child] = None
    control.execQueue.append(child)
    return child


def _waitAny(*children):
    """Waits on any child Future created by the calling Future.

    :param children: A tuple of children Future objects spawned by the calling
        Future.

    :return: A generator function that iterates on futures that are done.

    The generator produces results of the children in a non deterministic order
    that depends on the particular parallel execution of the Futures. The
    generator returns a tuple as soon as one becomes available."""
    n = len(children)
    # check for available results and index those unavailable
    for index, future in enumerate(children):
        if future.exceptionValue:
            raise future.exceptionValue
        if future._ended():
            future._delete()
            yield future
            n -= 1
        else:
            future.index = index
    future = control.current
    while n > 0:
        # wait for remaining results; switch to controller
        future.stopWatch.halt()
        childFuture = _controller.switch(future)
        future.stopWatch.resume()
        if childFuture.exceptionValue:
            raise childFuture.exceptionValue
        # Only yield if executed future was in children, otherwise loop
        if childFuture in children:
            childFuture._delete()
            yield childFuture
            n -= 1


def _waitAll(*children):
    """Wait on all child futures specified by a tuple of previously created
       Future.

    :param children: A tuple of children Future objects spawned by the calling
        Future.

    :return: A generator function that iterates on Future results.

    The generator produces results in the order that they are specified by
    the children argument. Because Futures are executed in a non deterministic
    order, the generator may have to wait for the last result to become
    available before it can produce an output. See waitAny for an alternative
    option."""
    for future in children:
        for f in _waitAny(future):
            yield f


def wait(fs, timeout=-1, return_when=ALL_COMPLETED):
    """Wait for the futures in the given sequence to complete.
    Using this function may prevent a worker from executing.

    :param fs: The sequence of Futures to wait upon.
    :param timeout: The maximum number of seconds to wait. If negative or not
        specified, then there is no limit on the wait time.
    :param return_when: Indicates when this function should return. The options
        are:

        ===============   ================================================
        FIRST_COMPLETED   Return when any future finishes or is cancelled.
        FIRST_EXCEPTION   Return when any future finishes by raising an
                          exception. If no future raises an exception then
                          it is equivalent to ALL_COMPLETED.
        ALL_COMPLETED     Return when all futures finish or are cancelled.
        ===============   ================================================

    :return: A named 2-tuple of sets. The first set, named 'done', contains the
        futures that completed (is finished or cancelled) before the wait
        completed. The second set, named 'not_done', contains uncompleted
        futures."""

    DoneAndNotDoneFutures = namedtuple('DoneAndNotDoneFutures', 'done not_done')
    if timeout < 0:
        # Negative timeout means blocking.
        if return_when == FIRST_COMPLETED:
            next(_waitAny(*fs))
        elif return_when in [ALL_COMPLETED, FIRST_EXCEPTION]:
            for _ in _waitAll(*fs):
                pass
        done = set(f for f in fs if f.done())
        not_done = set(fs) - done
        return DoneAndNotDoneFutures(done, not_done)

    elif timeout == 0:
        # Zero-value entry means non-blocking
        control.execQueue.flush()
        control.execQueue.updateQueue()
        done = set(f for f in fs if f._ended())
        not_done = set(fs) - done
        return DoneAndNotDoneFutures(done, not_done)

    else:
        # Any other value means blocking for a given time.
        done = set()
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Flush futures on local queue (to be executed remotely)
            control.execQueue.flush()
            # Block until data arrives (to free CPU time)
            control.execQueue.socket._poll(time.time() - start_time)
            # Update queue
            control.execQueue.updateQueue()

            for f in fs:
                if f._ended():
                    done.add(f)

            not_done = set(fs) - done

            if return_when == FIRST_COMPLETED and len(done) > 0:
                break
            if len(not_done) == 0:
                break
        return DoneAndNotDoneFutures(done, not_done)


def as_completed(fs, timeout=None):
    """Iterates over the given futures that yields each as it completes. This
    call is blocking.

    :param fs: The sequence of Futures to wait upon.
    :param timeout: The maximum number of seconds to wait. If None, then there
        is no limit on the wait time.

    :return: An iterator that yields the given Futures as they complete
        (finished or cancelled).
    """
    #TODO: Handle timeout
    return _waitAny(*fs)


def _join(child):
    """This private function is for joining the current Future with one of its
    child Future.

    :param child: A child Future object spawned by the calling Future.

    :return: The result of the child Future.

    Only one Future can be specified. The function returns a single
    corresponding result as soon as it becomes available."""
    for future in _waitAny(child):
        return future.resultValue


def _joinAll(*children):
    """This private function is for joining the current Future with all of the
    children Futures specified in a tuple.

    :param children: A tuple of children Future objects spawned by the calling
        Future.

    :return: A list of corresponding results for the children Futures.

    This function will wait for the completion of all specified child Futures
    before returning to the caller."""
    return [_join(future) for future in _waitAll(*children)]


def shutdown(wait=True):
    """This function is here for compatibility with `futures` (PEP 3148) and
    doesn't have any behavior.

    :param wait: Unapplied parameter."""
    pass
