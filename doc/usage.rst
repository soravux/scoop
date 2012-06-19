Usage
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

Architecture schema
-------------------

The future(s) distribution over workers is done via a blackboard pattern. In 
such pattern, workers act as independant elements which interacts with a 
blackboard to equilibrate their workload.

.. TODO: Add schema

.. note:
    
    The only available architecture of SCOOP 0.5 is the Blackboard Pattern, but 
    subsequent versions of SCOOP has been forecasted to support multiple 
    architectures.
    

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
This allows a finer control over the Futures, such as out-of-order processing.

    
How to launch SCOOP programs
----------------------------

The scoop module spawns the needed broker and workers on a given list of 
computers, including remote ones via ``ssh``.

.. program-output:: python -m scoop --help

Programs using SCOOP need to be launched with the ``-m scoop`` parameter 
passed to Python, as such::
    
    cd scoop/examples/
    python -m scoop -n 2 fullTree.py

A remote workers example may be as follow::

    python -m scoop --hosts 127.0.0.1 192.168.1.101 192.168.1.102 192.168.1.103 -vv -n 16 your_program.py [your arguments]

================    =================================
Argument
================    =================================
-m scoop
--hosts [...]
-vv
-n 16
your_program.py
[your arguments]
================    =================================
    
.. warning::

    Configure correctly your ``ssh`` instance. More information is available in the ref:`ssh-keys-information` section of the documentation.
    
.. note::
    
    Your local hostname must be externally routable for remote hosts to be able to connect to it. If you don't have a DNS properly setted up on your local network or a system hosts file, consider using the ``--broker-hostname`` argument to provide your externally routable IP or DNS name to SCOOP. You may as well be interested in the ``-e`` argument for testing purposes.
    
    
.. _examples-reference:

Cookbook
--------

Unordered processing
~~~~~~~~~~~~~~~~~~~~

You can :meth:`scoop.futures.wait` over desired Futures or unordered processing 
upon element arrival using :meth:`scoop.futures.as_completed` like so::

    from scoop import futures
    launches = [futures.submit(func, data) for i in range(10)]
    # The results will be ordered by execution time
    # the Future executed the fastest being the first element
    result = [i.result() for i in futures.as_completed(launches)]

    
Examples
--------
    
Examples are available in the ``examples/`` directory of scoop.

.. TODO discuss examples, literal include
    
Please check our :doc:`api` for any implentation detail of the proposed 
functions.

Startup scripts (supercomputer or grid)
---------------------------------------

You must provide a startup script on systems using a scheduler. Here is 
provided some example startup scripts using different grid task managers.

.. note::

    **Please note that these are only examples**. Refer to the documentation of 
    your own scheduler to get the list of every arguments you must and/or can 
    pass to be able the run the task on your grid.

Torque (Moab & Maui)
~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for Torque::

    #!/bin/bash
    ## Please refer to your grid documentation for available flags. This is only an example.
    #PBS -l procs=16
    #PBS -V
    #PBS -N SCOOPJob

    # Path to your executable. For example, if you extracted SCOOP to $HOME/downloads/scoop
    cd $HOME/downloads/scoop/examples

    # Add any addition to your environment variables like PATH. For example, if your local python installation is in $HOME/python
    export PATH=$HOME/python/bin:$PATH
    
    # If, instead, you are using the python offered by the system, you can stipulate it's library path via PYTHONPATH
    #export PYTHONPATH=$HOME/wanted/path/lib/python+version/site-packages/:$PYTHONPATH
    # Or use VirtualEnv via virtualenvwrapper here:
    #workon yourenvironment

    # Torque sets the list of nodes allocated to our task in a file referenced by the environment variable PBS_NODEFILE.
    hosts=$(cat $PBS_NODEFILE | sed ':a;N;$!ba;s/\n/ /g')
    
    # Launch SCOOP using the hosts
    time scooprun.py --hosts $hosts -vv -N 16 fullTree.py


Sun Grid Engine (SGE)
~~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for SGE::

    ## Please refer to your grid documentation for available flags. This is only an example.
    #$ -l h_rt=300
    #$ -pe test 16
    #$ -S /bin/bash
    #$ -cwd
    #$ -notify
    
    # Path to your executable. For example, if you extracted SCOOP to $HOME/downloads/scoop
    cd $HOME/downloads/scoop/examples
    
    # Add any addition to your environment variables like PATH. For example, if your local python installation is in $HOME/python
    export PATH=$HOME/python/bin:$PATH
    
    # If, instead, you are using the python offered by the system, you can stipulate it's library path via PYTHONPATH
    #export PYTHONPATH=$HOME/wanted/path/lib/python+version/site-packages/:$PYTHONPATH
    # Or use VirtualEnv via virtualenvwrapper here:
    #workon yourenvironment

    # Get a list of the (routable name) hosts assigned to our task
    hosts=$(cat $PE_HOSTFILE | awk '{printf "%s ", $1}')

    # Launch the remotes workers
    time scooprun.py --hosts $hosts -vv -N 16 test-scoop.py

.. TODO Condor & autres
        ~~~~~~

Pitfalls
--------

.. * Passing large data as parameter of the function
   * (Global variables? Todo?)
   
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


.. TODO: Or make a note with that:
   
SCOOP and greenlets
~~~~~~~~~~~~~~~~~~~

Since SCOOP uses greenlets to schedule and run futures, programs using 
greenlets won't work with SCOOP. However, you should consider replacing 
the greenlets in your code by SCOOP functions.
