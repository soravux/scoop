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

The script ``scooprun.py`` alows you to automatically spawn the needed brokers and workers on a given list of computer, including remote ones via ssh. It will automatically generate the environment variables needed for the execution of the parallel task.

To start a parallel task manually, you must launch a minimum of one broker. No workers are mandatory to execute a task with SCOOP, though it would defeat its purpose. Start any of the desired worker with its environment variables defining how to connect to it's broker. The following environment variables are used by the workers:

.. _Environment-variables-for-the-workers:

Environment variables for the workers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

====================  ============================================================================================  ========================
Environment Variable  Description                                                                                   Default value
====================  ============================================================================================  ========================
IS_ORIGIN             Set it to 1 if the worker is the origin of the task.                                          1
WORKER_NAME           The name of the current worker.                                                               origin
BROKER_NAME           The name of the broker the current worker will connect to.                                    broker
BROKER_ADDRESS        The address of the broker with protocol and port that the current worker will connect to.     ``tcp://127.0.0.1:5555``
====================  ============================================================================================  ========================

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