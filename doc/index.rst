
.. image:: images/logo.png
   :align: center
   :height: 140px

SCOOP (Scalable COncurrent Operations in Python) is a distributed task
module allowing concurrent parallel programming on various environments,
from heterogeneous grids to supercomputers.

Philosophy
----------

Our philosophy is based on these ideas:

    * Usage and interface ought to be standard and **simple**;
    * **Fast prototyping** allows precious time saving;
    * The **future** is parallel.
    
These tenets are translated concretely in a **minimum number of functions** 
allowing **maximum parallel efficiency** while keeping at **minimum the 
inner knowledge required** to use them. It is implemented in Python 3 in mind 
while being compatible with 2.6+ to allow fast prototyping without sacrificing 
efficiency and speed.

Features
--------

SCOOP features and advantages over 
`Futures <http://docs.python.org/dev/library/concurrent.futures.html>`_,
`multiprocessing <http://docs.python.org/dev/library/multiprocessing.html>`_ 
and similar modules are as follows:

    * Harness the power of **multiple computers** over network;
    * Ability to spawn multiple tasks inside a task;
    * API compatible with :pep:`3148`;
    * Parallelizing serial code with only minor modifications;
    * Efficient load-balancing.

Anatomy of a SCOOPed program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SCOOP can handle multiple diversified multi-layered tasks. With it, you can submit your different functions and data simultaneously and effortlessly while the framework execute them locally or remotely. Its **high flexibility** allows you to use it even inside functions already launched with SCOOP.

.. image:: images/introductory_tree.png
   :align: center
   :width: 600 px

Through SCOOP, you can execute simultaneously tasks that are different by 
nature, shown by the task color, or different by complexity, shown by the task radius. The module will handle the physical considerations of parallelization, such as task distribution over your resources (load balancing), communications, etc.

Applications
~~~~~~~~~~~~

The common applications of SCOOP consist but is not limited to:

    * Evolutionary Algorithms
    * Monte Carlo simulations
    * Data mining
    * Data processing
    * Graph traversal

Manual
------

.. toctree::
   :maxdepth: 2
   
   install
   usage
   api
   
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`