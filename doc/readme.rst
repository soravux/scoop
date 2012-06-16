Readme
======

Please refer to :doc:`setup` and :doc:`usage` for installation and usage instructions.


Nomenclature
------------

The nomenclature used to describe our architecture to execute parallel tasks is described in the following table:

.. _Nomenclature-table:

=========== =======================================================================================================================================
  Keyword   Description
=========== =======================================================================================================================================
Futures     A task, in the meaning of :pep:`3148#future-objects`.
Worker      Process executing and/or generating futures it received from or sending to its broker.
Origin      The worker executing the user program. Every other worker will wait for work dispatched as futures from the broker.
Broker      Process receiving and dispatching tasks to-and-fro its workers and/or other brokers. In charge of the load-balancing.
Federation  Conglomerate of brokers that works together on a task.
Main socket Router-Dealer (see the `ZeroMQ Guide <http://zguide.zeromq.org/page:all>`_) socket created between
Meta socket Publisher-Subscriber (see the `ZeroMQ Guide <http://zguide.zeromq.org/page:all>`_) socket created between the workers and brokers to propagate load and meta informations.
=========== =======================================================================================================================================


Requirements
------------

You may want to run your distributed and parallel tasks over a tightly integrated grid such as a supercomputer or you may want to test a bunch of computers laying there in the laboratory or put to good use some heterogeneous systems at home. SCOOP allows you to scale your parallel tasks to all these situations with minor modifications to your source code.

The software requirements for SCOOP is as follows:

* Python >= 2.7 or >= 3.2*
* Greenlets >= 0.3.4
* PyZMQ and libzmq >= 2.2.0

.. note::
    
    * Python versions earlier than 2.7 and 3.2 will work, but need the argparse module to be installed separately.    
    
SCOOP will work locally on any operating system that Python supports. For remote connexions to work, you will need the ``ssh`` executable to be properly installed on the machine. More information is available in the ref:`ssh-keys-information` section of the documentation.

Please check the document :doc:`setup` for more technical informations about the setup of a working SCOOP system.
