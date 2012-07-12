
=====

Nomenclature
------------

.. _Nomenclature-table:

=========== =======================================================================================================================================
  Keyword   Description
=========== =======================================================================================================================================
Future(s)   The Future class encapsulates the asynchronous execution of a callable.
Broker      Dispatch Futures.
Worker      Process executing Futures.
Origin      The worker executing the user program.
=========== =======================================================================================================================================

Architecture diagram
--------------------

The future(s) distribution over workers is done by a 
`Broker pattern <http://zguide.zeromq.org/page:all#A-Request-Reply-Broker>`_. 
In such pattern, workers act as independant elements which interacts with a 
broker to mediate their communications.

.. image:: images/architecture.png
   :align: center

.. note:
    
    The only available architecture of SCOOP 0.5 is the Broker pattern, but 
    subsequent versions of SCOOP has been forecasted to support multiple 
    architectures.
    

How to use SCOOP in your code
-----------------------------

The philosophy of SCOOP is loosely built around the *futures* module proposed 
by :pep:`3148`. It primarily defines a :meth:`scoop.futures.map` and a 
:meth:`scoop.futures.submit` function allowing asynchroneous computation which 
SCOOP will propagate to its workers. 

:meth:`scoop.futures.map` returns a generator over the results in-order. It can 
thus act as a parallel substitute to the standard |map()|_, for instance::



.. |map()| replace:: *map()*
.. _map(): http://docs.python.org/library/functions.html#map

:meth:`scoop.futures.submit` returns a :class:`scoop.types.Future` instance. 
This allows a finer control over the Futures, such as out-of-order processing.

.. _examples-reference:

Examples
~~~~~~~~
    
Examples are available in the ``examples/`` directory of scoop. For instance, 
a Monte-Carlo method of calculating Pi using Scoop to parallelize its 
computation is found in *examples/piCalc.py*:

.. literalinclude:: ../examples/piCalc.py
   :lines: 21-

The *examples/fullTree.py* example holds a pretty good wrap-up of available
functionnalities:

.. literalinclude:: ../examples/fullTree.py
   :lines: 21-
    
Please check our :doc:`api` for any implentation detail of the proposed 
functions.

Cookbook
--------

Unordered processing
~~~~~~~~~~~~~~~~~~~~

You can iterate over desired Futures upon element arrival for unordered 
processing using :meth:`scoop.futures.as_completed` like so::

    from scoop import futures
    launches = [futures.submit(func, data) for i in range(10)]
    # The results will be ordered by execution time
    # the Future executed the fastest being the first element
    result = [i.result() for i in futures.as_completed(launches)]
    
How to launch SCOOP programs
----------------------------

The scoop module spawns the needed broker and workers on a given list of 
computers, including remote ones via ``ssh``.

Programs using SCOOP need to be launched with the ``-m scoop`` parameter 
passed to Python, as such::
    
    cd scoop/examples/
    python -m scoop -n 2 fullTree.py
    
Here is a list of the parameters that can be passed to scoop::

    python -m scoop --help
    usage: python -m scoop [-h] [--hosts [HOSTS [HOSTS ...]]]
                           [--path PATH] [--nice NICE] [--verbose]
                           [--log LOG] [-n N] [-e]
                           [--broker-hostname BROKER_HOSTNAME]
                           [--python-executable PYTHON_EXECUTABLE]
                           [--pythonpath PYTHONPATH] [--debug]
                           executable ...

    Starts a parallel program using SCOOP.

    positional arguments:
      executable            The executable to start with SCOOP
      args                  The arguments to pass to the executable

    optional arguments:
      -h, --help            show this help message and exit
      --hosts [HOSTS [HOSTS ...]], --host [HOSTS [HOSTS ...]]
                            The list of hosts. The first host will execute the
                            origin.
      --path PATH, -p PATH  The path to the executable on remote hosts
      --nice NICE           *nix niceness level (-20 to 19) to run the executable
      --verbose, -v         Verbosity level of this launch script (-vv for more)
      --log LOG             The file to log the output (default is stdout)
      -n N                  Number of process to launch the executable with
      -e                    Activate ssh tunnels to route toward the broker
                            sockets over remote connections (may eliminate routing
                            problems and activate encryption but slows down
                            communications)
      --broker-hostname BROKER_HOSTNAME
                            The externally routable broker hostname / ip (defaults
                            to the local hostname)
      --python-executable PYTHON_EXECUTABLE
                            The python executable with which to execute the script
      --pythonpath PYTHONPATH
                            The PYTHONPATH environment variable
      --debug               Turn on the debuging

A remote workers example may be as follow::

    python -m scoop --hosts 127.0.0.1 remotemachinedns 192.168.1.101 192.168.1.102 192.168.1.103 -vv -n 16 your_program.py [your arguments]

================    =================================
Argument            Meaning
================    =================================
-m scoop            **Mandatory** Uses SCOOP to run program.
--hosts [...]       List of hosts to launch workers on.
-vv                 Double verbosity flag
-n 16               Launch 16 workers
your_program.py     The program to be launched
[your arguments]    The arguments that needs to be passed to your program
================    =================================

.. note::
    
    Your local hostname must be externally routable for remote hosts to be able to connect to it. If you don't have a DNS properly set up on your local network or a system hosts file, consider using the ``--broker-hostname`` argument to provide your externally routable IP or DNS name to SCOOP. You may as well be interested in the ``-e`` argument for testing purposes.

Startup scripts (supercomputer or grid)
---------------------------------------

You must provide a startup script on systems using a scheduler. Here is 
provided some example startup scripts using different grid task managers. They
are available in the ``examples/submitFiles`` directory.

.. note::

    **Please note that these are only examples**. Refer to the documentation of 
    your scheduler for the list of arguments needed to run the task on your 
    grid.

Torque (Moab & Maui)
~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for Torque::

.. literalinclude:: ../examples/submitFiles/Torque.sh


Sun Grid Engine (SGE)
~~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for SGE:

.. literalinclude:: ../examples/submitFiles/SGE.sh

.. TODO Condor & autres
        ~~~~~~

Pitfalls
--------

.. * (Global variables? Todo?)

Program scope
~~~~~~~~~~~~~

.. Link to PEP that states this

As a good Python practice, you should always wrap the executable part of your 
program using::

  if __name__ == '__main__':

This is mandatory when using parallel frameworks such as multiprocessing and 
SCOOP. Otherwise, each worker (or equivalent) will try to execute your code 
serially.
   
Evaluation laziness
~~~~~~~~~~~~~~~~~~~

The :meth:`scoop.futures.map` and :meth:`scoop.futures.submit` functions are 
lazy, meaning that it won't start computing locally until you access the 
generator it returned. However, these function can start executing on remote 
worker the moment they are submited. Events that will trigger evaluation are 
element access such as iteration. To force immediate evaluation, you can wrap 
your call with a list, such as::

    from scoop import futures
    
    def add(x, y): return x + y
    
    if __name__ == "__main__":
        results = list(futures.map(add, range(8), range(8)))   

Large datasets
~~~~~~~~~~~~~~

Every parameter sent to a function by a :meth:`scoop.futures.map` or 
:meth:`scoop.futures.submit` gets serialized and sent within the Future to its
worker. Consider using a global variable in your module scope for passing large
elements; it will then be loaded on launch by every worker and won't overload
your network.
Incorrect::

    from scoop import futures
    
    if __name__ == '__main__':
        results = list(futures.map(sum, zip(*([range(8)])*(2**16))))

Better::

    from scoop import futures

    data = ([range(8)])*(2**16)

    def mySum(inIndex):
      return sum(data[inIndex])
    
    if __name__ == '__main__':
        results = list(futures.map(sum, range(8)))
   
SCOOP and greenlets
~~~~~~~~~~~~~~~~~~~

Since SCOOP uses greenlets to schedule and run futures, programs using 
greenlets won't work with SCOOP. However, you should consider replacing 
the greenlets in your code by SCOOP functions.
