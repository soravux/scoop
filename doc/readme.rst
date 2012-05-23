README
======

Nomenclature
------------

The terminology used to describe our architecture to execute parallel tasks is described in the following table:

.. _Nomenclature-table:

=========== =================================================================================================================
  Keyword   Description
=========== =================================================================================================================
Federation  Conglomerate of brokers that works together on a task.
Broker      Process dispatching tasks to its workers and/or other brokers and managing the load-balancing.   
Worker      Process executing tasks it received from its broker, potentially generating and sending tasks back to the broker.
Origin      Special status of a worker stating that he spawns the root task and that it will receive the task answer.
Meta socket Extraneous Publisher-Subscriber socket created between the brokers to propagate load informations.
=========== =================================================================================================================


How to use SCOOP in your code
-----------------------------

The philosophy of SCOOP is loosely built around the *futures* module proposed by :pep:`3148`. It primarily defines a ``map()`` and a ``submit()`` function allowing asynchroneous computation which SCOOP will propagate to a distributed grid of workers. The usage of these functions are compatible with their official counterparts, for instance you could replace a standard python ``map()`` call by the same function in SCOOP to obtain a parallel version of this task.
Please check our :doc:`api` for any implentation detail of the proposed functions.

You should also be aware that your main function, meaning your parent function that will contain calls to the functions listed in :doc:`api` such as  `map()``, must be launched using the ``futures.startup()``. This ensures the proper initialization of SCOOP.

Evaluation laziness
~~~~~~~~~~~~~~~~~~~

The ``map()`` and ``submit()`` functions are lazy, meaning that it won't start computing until you access the generator it returned. Events that will trigger evaluation are element access such as iteration. To force immediate evaluation, you can wrap your call with a list, such as::

    from scoop import futures
    
    def add(x, y): return x+y
        
    def main():
        results = list(futures.map(add, range(8)))
    
    futures.startup(main)

How to launch a task
--------------------

Requirements
~~~~~~~~~~~~

You may want to run your distributed and parallel tasks over a tightly integrated grid such as a supercomputer or you may want to test a bunch of computers laying there in the laboratory or put to good use some heterogeneous systems at home. SCOOP allows you to scale your parallel tasks to all these situations with minor modifications to your source code.

The software requirements for SCOOP is as follows:

* Python >= 2.6
* argparse >= 1.2.1 (for python 2.6)
* Greenlets >= 0.3.4
* PyZMQ as well as libzmq >= 2.2.0

SCOOP works with Linux and Windows. If you launch tasks from the latter, be sure to have Cygwin installed and your PATH environment variable setted correctly in order to be able to launch tasks remotely, since this feature uses ``ssh``.

Please check the document :doc:`setup` for more technical informations about the setup of a working SCOOP system.

scooprun.py script
~~~~~~~~~~~~~~~~~~

The script ``scooprun.py`` spawns the needed brokers and workers on a given list of computer, including remote ones via ``ssh``.

You can pass the argument ``--help`` to scooprun.py to get the list of available arguments.

An usage example may be as follow::

    scooprun.py --hosts 127.0.0.1 192.168.1.101 192.168.1.102 192.168.1.103 -vv -n 16 your_program.py

This will run a local broker, 4 workers on each 3 remotes hosts as well as the local machine that will execute ``you_program.py``.

.. note::

    Keep in mind that connecting to remote hosts is be done without a prompt. Ensure that you have properly created ssh keys that allows for passwordless authentication over ssh on your remote hosts, as stated in :ref:`ssh-keys-information`.
    
.. note::
    
    Your local hostname must be externally routable for remote hosts to be able to connect to it. If you don't have a DNS properly setted up on your local network or a system hosts file, consider using the ``--broker-hostname`` argument to provide your externally routable IP or DNS name to ``scooprun.py``. You may as well be interested in the ``-e`` argument for testing purposes.
    
Manual launch
~~~~~~~~~~~~~

To start a parallel task manually using SCOOP, you must launch a minimum of one broker and one worker, acting as the origin. Manually launching a SCOOP task can be summarised to:

#. Start a broker;
#. Start the desired non-origin workers.
#. Start the origin worker.

The workers need to connect to their respective broker. The path to their broker is stated in environment variables, described below.

.. _Environment-variables-for-the-workers:

Environment variables for the workers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

====================  =====================================================================================================  ========================
Environment Variable  Description                                                                                            Default value
====================  =====================================================================================================  ========================
IS_ORIGIN             Set it to 1 if the worker is the origin of the task.                                                   1
WORKER_NAME           The name of the current worker.                                                                        origin
BROKER_NAME           The name of the broker the current worker will connect to.                                             broker
BROKER_ADDRESS        The address of the broker task socket with protocol and port that the current worker will connect to.  ``tcp://127.0.0.1:5555``
META_ADDRESS          The address of the broker meta socket with protocol and port that the current worker will connect to.  ``tcp://127.0.0.1:5556``
====================  =====================================================================================================  ========================

.. _Environment-variables-for-the-brokers:

Environment variables for the brokers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

====================  ============================================================================================  ==========================================
Environment Variable  Description                                                                                   Default value
====================  ============================================================================================  ==========================================
BROKER_NAME           The name of this broker.                                                                      broker
BROKER_ADDRESSES      List of other brokers assigned to the current task                                            [Empty]
META_ADDRESSES        List of other brokers The address of the meta socket with protocol and port                   ['BROKER_ADDRESSES' with port incremented]
====================  ============================================================================================  ==========================================

.. warning::

    Be sure to launch every process using the SCOOP API using the same Python version. SCOOP uses Python serialisation which is known to be incompatible between versions. Using different Python versions, on a remote worker or locally, could lead in misinterpreted deserialisation. This translates to cryptic and indecipherable errors which the Python traceback could probably misidentify.