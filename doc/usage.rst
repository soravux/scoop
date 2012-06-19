Usage
=====

How to launch SCOOP programs
----------------------------

The scoop module spawns the needed brokers and workers on a given list of 
computer, including remote ones via ``ssh``.

.. TODO show ``python -m scoop --help`` output here

Programs using SCOOP needs to be launched with the ``-m scoop`` parameter 
passed to Python, as such::
    
    cd scoop/examples/
    python -m scoop -n 2 fullTree.py

A remote workers example may be as follow::

    python -m scoop --hosts 127.0.0.1 192.168.1.101 192.168.1.102 192.168.1.103 -vv -n 16 your_program.py [your arguments]

This will run a local broker, 4 workers on each 3 remotes hosts as well as the 
local machine that will execute ``you_program.py`` and pass
``[your arguments]`` to it.

.. warning::

    Configure correctly your ``ssh`` instance. More information is available in the ref:`ssh-keys-information` section of the documentation.
    
.. note::
    
    Your local hostname must be externally routable for remote hosts to be able to connect to it. If you don't have a DNS properly setted up on your local network or a system hosts file, consider using the ``--broker-hostname`` argument to provide your externally routable IP or DNS name to ``scooprun.py``. You may as well be interested in the ``-e`` argument for testing purposes.
    
    
.. _examples-reference:
    
Examples
--------
    
Examples are available in the ``examples/`` directory of scoop.

.. TODO discuss examples
    
Please check our :doc:`api` for any implentation detail of the proposed 
functions.

How to use SCOOP in your code
-----------------------------

The philosophy of SCOOP is loosely built around the *futures* module proposed 
by :pep:`3148`. It primarily defines a :meth:`scoop.futures.map` and a 
:meth:`scoop.futures.submit` function allowing asynchroneous computation which 
SCOOP will propagate to its workers. 

:meth:`scoop.futures.map` returns a generator over the results in-order. It can 
thus act as a parallel substitute to the standard |map()|_.

.. |map()| replace:: *map()*
.. _map(): http://docs.python.org/library/functions.html#map

:meth:`scoop.futures.submit` returns a :class:`scoop.types.Future` instance. 
This allows a finer control over the Futures, such as 
:meth:`scoop.futures.wait` over desired Futures or unordered processing upon 
element arrival using :meth:`scoop.futures.as_completed` like so::

    from scoop import futures
    launches = [futures.submit(func, data) for i in range(10)]
    # The results will be ordered by execution time
    # the Future executed the fastest being the first element
    result = [i.result() for i in futures.as_completed(launches)]

Evaluation laziness
~~~~~~~~~~~~~~~~~~~

The ``map()`` and ``submit()`` functions are lazy, meaning that it won't start 
computing locally until you access the generator it returned. However, these 
function can start executing on remote worker the moment they are submited. 
Events that will trigger evaluation are element access such as iteration. To 
force immediate evaluation, you can wrap your call with a list, such as::

    from scoop import futures
    
    def add(x, y): return x+y
    
    def main():
        results = list(futures.map(add, range(8), range(8)))
    
    futures.startup(main)


SCOOP and greenlets
-------------------

Since SCOOP uses greenlets to schedule and run futures, programs using 
greenlets won't work with SCOOP. However, you should consider replacing 
the greenlets in your code by SCOOP functions.
