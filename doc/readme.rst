README
======

Nomenclature
------------

The nomenclature of our architecture to exectute tasks on a parallel distribution is described in the following table:

.. _Nomenclature-table:

=========== ==================================================================================================
  Keyword   Description
=========== ==================================================================================================
Federation  Conglomerate of brokers that works together on a task.
Broker      Process dispatching tasks to its workers and/or other brokers and managing the load-balancing.   
Worker      Process executing tasks it received from its broker.
Meta socket Extraneous Publisher-Subscriber socket created between the brokers to propagate load informations.
=========== ==================================================================================================


How to use SCOOP in your code
-----------------------------

The philosophy of SCOOP is build around the *futures* module proposed by :pep:`3148`. It defines ``map()`` and ``join()`` functions allowing asynchroneous computation which SCOOP will propagate to it's local and foreign workers.
Please check our :doc:`api` for any details of implentation of the proposed functions.

You should also be aware that your main function, meaning your parent function that will contain multiple ``map()`` and ``join()``, must be launched using the ``futures.startup()``. This ensures the proper initialization of SCOOP.


How to launch a task
--------------------

Requirements
~~~~~~~~~~~~

You may want to run your distributed and parallel tasks over a tightly integrated grid such as a supercomputer or you may want to test a bunch of computers laying there in the laboratory of put to good use some heterogeneous systems at home. SCOOP allows you to scale your parallel tasks to all these situations without modification to your source code.

* argparse >= 1.2.1 (for python 2.6)
* Python >= 2.6
* Greenlets >= 0.3.4
* PyZMQ as well as libzmq >= 2.2.0

SCOOP works with Linux and Windows. On the latter, be sure to have Cygwin installed and your PATH environment variable setted correctly in order to be able to launch tasks remotely, since this feature uses ``ssh``.

If you can't modify the system-wide python installation, you should install the requirements using::

    python setup.py install --prefix=/home/your_username/your_desired_python_lib_path/

This way, you will be able to invoke your program after setting the environment variable (``export PYTHONPATH=$PYTHONPATH:/home/your_username/your_desired_python_lib_path/`` for the given example).

scooprun.py script
~~~~~~~~~~~~~~~~~~

The script ``scooprun.py`` allows you to automatically spawn the needed brokers and workers on a given list of computer, including remote ones via ssh.

You can pass the argument ``--help`` to scooprun.py to get the list of available arguments.

An usage example may be as follow::

    scooprun.py --hosts 127.0.0.1 192.168.1.101 192.168.1.102 192.168.1.103 -vv -N 16 your_program.py

This will run 4 workers on each 3 remotes hosts as well as the local machine that will execute ``you_program.py``.

.. note::

    Please keep in mind that connecting to remote hosts must be done without a shell, meaning that you possibly won't be able to write your password when ssh asks for it. Ensure that you have properly created ssh keys that allows for passwordless authentication over ssh on your remote hosts.
    
    If your remote hosts needs special configuration (non-default port, some specified username, etc.), you should do it in your ssh client configuration file (by default ``~/.ssh/config``). Please refer to the ssh manual as to how to configure and personalize your hosts connections.
    
.. note::
    
    Bear in mind that your local hostname must be externally routable for remote hosts to be able to connect to it. If you don't have a DNS properly setted up on your local network or a system hosts file, consider using the ``--broker-hostname`` argument to provide your externally routable IP or DNS name.
    
Manual launch
~~~~~~~~~~~~~

To start a parallel task manually, you must launch a minimum of one broker. No workers are mandatory to execute a task with SCOOP, though it would defeat its purpose. Start any of the desired worker with its environment variables defining how to connect to it's broker. The following environment variables are used by the workers:

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

    Be sure to launch every process using the SCOOP API using the same Python version. SCOOP uses Python serialisation which is known to be incompatible between versions. Using different Python versions, on a remote worker or locally, could lead in misinterpreted deserialisation which means cryptic and indecipherable errors which the Python traceback could probably misidentify.