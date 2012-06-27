Welcome to SCOOP's documentation!
=================================

SCOOP (Scalable COncurrent Operations in Python) is a distributed task
module allowing concurrent parallel programming on various environments,
from heterogeneous grids to supercomputers.

Our philosophy is based on these ideas:

    * Usage and interface ought to be standard and **simple**;
    * **Fast prototyping** allows precious time saving;
    * The **future** is parallel.

SCOOP features and advantages over 
`Futures <http://docs.python.org/dev/library/concurrent.futures.html>`_,
`multiprocessing <http://docs.python.org/dev/library/multiprocessing.html>`_ 
and similar modules are as follows:

    * Harness the power of **multiple computers** over network.
    * Ability to spawn multiple tasks inside a task;
    * API compatible with :pep:`3148`;
    * Parallelizing serial code with only minor modifications;
    * Intelligent load-balancing (*Currently being developped*);

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