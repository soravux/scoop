Configuration
=============

Manually launch SCOOP
---------------------
To start a parallel task manually using SCOOP, you must launch a minimum of one broker and one worker, acting as the origin. Manually launching a SCOOP task can be summarised to:

#. Start a broker;
#. Start the desired non-origin workers;
#. Start the origin worker.

The workers need to connect to their respective broker. The path to their broker is stated in environment variables as described below.

The brokers are configured using arguments passed while launching them. You can get the list of their arguments by launching ``python broker.py --help`` in the root directory of SCOOP.

.. warning::

    Be sure to launch every process using the SCOOP API using the same Python version. SCOOP uses Python serialisation which is known to be incompatible between versions. Using different Python versions, on a remote worker or locally, could lead in misinterpreted deserialisation. This translates to cryptic and indecipherable errors which the Python traceback could probably misidentify.
    
.. _Environment-variables-for-the-workers:

Environment variables for the workers
-------------------------------------

====================  =====================================================================================================  ========================
Environment Variable  Description                                                                                            Default value
====================  =====================================================================================================  ========================
IS_ORIGIN             Set it to 1 if the worker is the origin of the task.                                                   1
WORKER_NAME           The name of the current worker.                                                                        origin
BROKER_NAME           The name of the broker the current worker will connect to.                                             broker
BROKER_ADDRESS        The address of the broker task socket with protocol and port that the current worker will connect to.  ``tcp://127.0.0.1:5555``
META_ADDRESS          The address of the broker meta socket with protocol and port that the current worker will connect to.  ``tcp://127.0.0.1:5556``
====================  =====================================================================================================  ========================
