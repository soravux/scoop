Usage
=====

How to use SCOOP in your code
-----------------------------

The philosophy of SCOOP is loosely built around the *futures* module proposed by :pep:`3148`. It primarily defines a :meth:`scoop.futures.map` and a :meth:`scoop.futures.submit` function allowing asynchroneous computation which SCOOP will propagate to a distributed grid of workers. 

:meth:`scoop.futures.map` returns a generator over the results and can act as a parallel substitute to the standard |map()|_. Results will be ordered as they are iterated upon.

.. |map()| replace:: *map()*
.. _map(): http://docs.python.org/library/functions.html#map

:meth:`scoop.futures.submit` returns a :class:`scoop.types.Future` instance. This allows a finer control over the Futures, such as :meth:`scoop.futures.wait` over desired Futures or unordered processing upon element arrival using :meth:`scoop.futures.as_completed` like so::

    from scoop import futures
    launches = [futures.submit(func, data) for i in range(10)]
    # The results will be ordered by execution time
    # the Future executed the fastest being the first element
    result = [i.result() for i in futures.as_completed(launches)]

Examples are available in the ``examples/`` directory of scoop.
    
Please check our :doc:`api` for any implentation detail of the proposed functions.

Evaluation laziness
~~~~~~~~~~~~~~~~~~~

The ``map()`` and ``submit()`` functions are lazy, meaning that it won't start computing until you access the generator it returned. Events that will trigger evaluation are element access such as iteration. To force immediate evaluation, you can wrap your call with a list, such as::

    from scoop import futures
    
    def add(x, y): return x+y
        
    def main():
        results = list(futures.map(add, range(8), range(8)))
    
    futures.startup(main)