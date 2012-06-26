Welcome to SCOOP's documentation!
=================================

SCOOP (Scalable COncurrent Operations in Python) is a distributed task
module allowing concurrent parallel programming on various environments,
from motley grids to supercomputers.

Our philosophy is based on these ideas:

    * **Simplicity** and standard usage and interface are essential;
    * **Fast prototyping** allows precious time saving;
    * The **future** is parallel.

SCOOP features and advantages over 
`Futures <http://docs.python.org/dev/library/concurrent.futures.html>`_,
`Multiprocessing <http://docs.python.org/dev/library/multiprocessing.html>`_ 
and similar modules are as follows:

    * API compatible with :pep:`3148`;
    * Parallelizing with only minor modifications to serial code;
    * Intelligent load-blancing (*Currently being developped*);
    * Ability to spawn multiple futures (tasks) inside a future;
    * Harness the power of **multiple computers** over network.

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