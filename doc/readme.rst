Readme
======

Please refer to :doc:`setup` and :doc:`usage` for installation and usage instructions.


Nomenclature
------------

The nomenclature used to describe our architecture to execute parallel tasks is described in the following table:

.. _Nomenclature-table:

=========== ==============================================================================================================================================================
  Keyword   Description
=========== ==============================================================================================================================================================
Futures     A task, in the meaning of :pep:`3148#future-objects`.
Worker      Process executing and/or generating futures it received from or sending to its broker.
Origin      The worker executing the user program. Every other worker will wait for work dispatched as futures from the broker.
Broker      Process receiving and dispatching tasks to-and-fro its workers and/or other brokers. In charge of the load-balancing.
Federation  Conglomerate of brokers that works together on a task.
Main socket Router-Dealer (see the `ZeroMQ Guide <http://zguide.zeromq.org/page:all>`_) socket created between
Meta socket Publisher-Subscriber (see the `ZeroMQ Guide <http://zguide.zeromq.org/page:all>`_) socket created between the workers and brokers to propagate load and meta informations.
=========== ==========================================================================================================================================================================


Requirements
------------

You may want to run your distributed and parallel tasks over a tightly integrated grid such as a supercomputer or you may want to test a bunch of computers laying there in the laboratory or put to good use some heterogeneous systems at home. SCOOP allows you to scale your parallel tasks to all these situations with minor modifications to your source code.

The software requirements for SCOOP is as follows:

* Python >= 2.7 or >= 3.2*
* Greenlets >= 0.3.4
* PyZMQ and libzmq >= 2.2.0

.. note::
    
    * Python versions earlier than 2.7 and 3.2 will work, but need the argparse module to be installed separately.    
    
SCOOP will work locally on any operating system that Python supports. For remote connexions to work, you will need the ``ssh`` executable to be properly installed on the machine.

Please check the document :doc:`setup` for more technical informations about the setup of a working SCOOP system.


Program launch
--------------

The scoop module spawns the needed brokers and workers on a given list of computer, including remote ones via ``ssh``.

You can execute ``python -m scoop --help`` to get the list of available arguments.

An usage example may be as follow::

    python -m scoop --hosts 127.0.0.1 192.168.1.101 192.168.1.102 192.168.1.103 -vv -n 16 your_program.py [your arguments]

This will run a local broker, 4 workers on each 3 remotes hosts as well as the local machine that will execute ``you_program.py`` with ``[your arguments]``.

.. note::

    Keep in mind that connecting to remote hosts is be done without a prompt. Ensure that you have properly created ssh keys that allows for passwordless authentication over ssh on your remote hosts, as stated in :ref:`ssh-keys-information`.
    
.. note::
    
    Your local hostname must be externally routable for remote hosts to be able to connect to it. If you don't have a DNS properly setted up on your local network or a system hosts file, consider using the ``--broker-hostname`` argument to provide your externally routable IP or DNS name to ``scooprun.py``. You may as well be interested in the ``-e`` argument for testing purposes.