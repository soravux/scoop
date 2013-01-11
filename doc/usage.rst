Usage
=====

Nomenclature
------------

.. _Nomenclature-table:

=========== =======================================================================================================================================
  Keyword   Description
=========== =======================================================================================================================================
Future(s)   The Future class encapsulates the asynchronous execution of a callable.
Broker      Process dispatching Futures.
Worker      Process executing Futures.
Root        The worker executing the root Future.
=========== =======================================================================================================================================

Architecture diagram
--------------------

The future(s) distribution over workers is done by a variation of the 
`Broker pattern <http://zguide.zeromq.org/page:all#A-Request-Reply-Broker>`_. 
In such a pattern, workers act as independant elements that interact with a 
broker to mediate their communications.

.. image:: images/architecture.png
   :height: 250px
   :align: center

How to use SCOOP in your code
-----------------------------

The philosophy of SCOOP is loosely built around the *futures* module proposed 
by :pep:`3148`. It primarily defines a :meth:`~scoop.futures.map` and a 
:meth:`~scoop.futures.submit` function allowing asynchroneous computation that 
SCOOP will propagate to its workers.

Map
~~~

A |map()|_ function applies multiple parameters to a single function. For 
example, if you want to apply the |abs()|_ function to every number of a list::

    import random
    data = [random.randint(-1000,1000) for r in range(1000)]
    
    # Without Map
    result = []
    for i in data:
      result.append(abs(i))

    # Using a Map
    result = list(map(abs, data))

.. |abs()| replace:: *abs()*
.. _abs(): http://docs.python.org/library/functions.html#abs

SCOOP's :meth:`~scoop.futures.map` returns a generator iterating over the
results in the same order as its inputs. It can thus act as a parallel
substitute to the standard |map()|_, for instance::

    # Script to be launched with: python -m scoop scriptName.py
    import random
    from scoop import futures
    data = [random.randint(-1000, 1000) for r in range(1000)]

    if __name__ == '__main__':
        # Python's standard serial function
        dataSerial = list(map(abs, data))

        # SCOOP's parallel function
        dataParallel = list(futures.map(abs, data))

        assert dataSerial == dataParallel

.. |map()| replace:: *map()*
.. _map(): http://docs.python.org/library/functions.html#map

.. _test-for-main-mandatory:

.. warning::
    In your root program, you *must* check ``if __name__ == __main__`` as
    show above.
    Failure to do so will result in every worker trying to run their own 
    instance of the program. This ensures that every worker waits for 
    parallelized tasks spawned by the root worker.

.. note::
    Your callable function passed to SCOOP must be picklable in its entirety.

    The pickle module is limited to **top level functions and classes** as
    stated in the 
    `documentation <http://docs.python.org/3/library/pickle.html#what-can-be-pickled-and-unpickled>`_.

.. note::
    Functions executed using SCOOP must return a value.

.. note::
    Keep in mind that objects are not shared between workers and that changes
    made to an object in a function are not seen by other workers.

Submit
~~~~~~

SCOOP's :meth:`~scoop.futures.submit` returns a :class:`~scoop._types.Future` 
instance. 
This allows a finer control over the Futures, such as out-of-order results 
retrieval.

mapReduce
~~~~~~~~~

The :meth:`~scoop.futures.mapReduce` function of SCOOP allows to parallelize a
reduction function after applying the aforementionned
:meth:`~scoop.futures.map` function.
It returns a single value.

A reduction function takes the map results and applies a function cumulatively
to it.
For example, applying `reduce(lambda x, y: x+y, ["a", "b", "c", "d"])` would
execute `(((("a")+"b")+"c")+"d")` give you the result `"abcd"`

Read the standard Python
`reduce <http://docs.python.org/3.0/library/functools.html#functools.reduce>`_
function for more information.

A common reduction usage consist of a sum as the following example::

    # Script to be launched with: python -m scoop scriptName.py
    import random
    import operator
    from scoop import futures
    data = [random.randint(-1000, 1000) for r in range(1000)]
    

    if __name__ == '__main__':
        # Python's standard serial function
        serialSum = sum(map(abs, data))

        # SCOOP's parallel function
        parallelSum = futures.mapReduce(abs, operator.add, data)

        assert serialSum == parallelSum

.. note::
    You can pass any arbitrary reduction function, not only operator ones.


mapScan
~~~~~~~



Examples
--------

Examples are available in the |exampleDirectory|_ directory of SCOOP.

.. |exampleDirectory| replace:: :file:`examples/`
.. _exampleDirectory: https://code.google.com/p/scoop/source/browse/examples/

Please refer to the :doc:`examples` page where detailed explanations are
available.


How to launch SCOOP programs
----------------------------

The scoop module spawns the needed broker and workers on a given list of 
computers, including remote ones via :program:`ssh`.

Programs using SCOOP need to be launched with the :option:`-m scoop` parameter 
passed to Python, as such::
    
    cd scoop/examples/
    python -m scoop fullTree.py

.. note::
  When using a Python version prior to 2.7, you must start SCOOP using 
  :option:`-m scoop.__main__`.

  You should also consider using an up-to-date version of Python.
    
Here is a list of the parameters that can be passed to SCOOP::

    python -m scoop --help
    usage: python -m scoop [-h]
                           [--hosts [HOSTS [HOSTS ...]] | --hostfile HOSTFILE]
                           [--path PATH] [--nice NICE]
                           [--verbose] [--log LOG] [-n N]
                           [-e] [--broker-hostname BROKER_HOSTNAME]
                           [--python-executable PYTHON_EXECUTABLE]
                           [--pythonpath PYTHONPATH]
                           executable ...

    Starts a parallel program using SCOOP.

    positional arguments:
      executable            The executable to start with SCOOP
      args                  The arguments to pass to the executable

    optional arguments:
      -h, --help            show this help message and exit
      --hosts [HOSTS [HOSTS ...]], --host [HOSTS [HOSTS ...]]
                            The list of hosts. The first host will execute the
                            root program. (default is 127.0.0.1)
      --hostfile HOSTFILE   The hostfile name
      --path PATH, -p PATH  The path to the executable on remote hosts (default 
                            is local directory)
      --nice NICE           *nix niceness level (-20 to 19) to run the executable
      --verbose, -v         Verbosity level of this launch script (-vv for more)
      --log LOG             The file to log the output (default is stdout)
      -n N                  Total number of workers to launch on the hosts.
                            Workers are spawned sequentially over the hosts.
                            (ie. -n 3 with 2 hosts will spawn 2 workers on the
                            first host and 1 on the second.) (default: Number of
                            CPUs on current machine)
      -e                    Activate ssh tunnels to route toward the broker
                            sockets over remote connections (may eliminate routing
                            problems and activate encryption but slows down
                            communications)
      --broker-hostname BROKER_HOSTNAME
                            The externally routable broker hostname / ip (defaults
                            to the local hostname)
      --python-executable PYTHON_EXECUTABLE
                            The python executable with which to execute the script
      --pythonpath PYTHONPATH
                            The PYTHONPATH environment variable (default is 
                            current PYTHONPATH)

A remote workers example may be as follow::

    python -m scoop --hostfile hosts -vv -n 6 your_program.py [your arguments]

================    =================================
Argument            Meaning
================    =================================
-m scoop            **Mandatory** Uses SCOOP to run program.
--hostfile          hosts is a file containing a list of host to launch SCOOP
-vv                 Double verbosity flag.
-n 6                Launch a total of 6 workers.
your_program.py     The program to be launched.
[your arguments]    The arguments that needs to be passed to your program.
================    =================================

.. note::
    Your local hostname must be externally routable for remote hosts to be able to connect to it. If you don't have a DNS properly set up on your local network or a system hosts file, consider using the :option:`--broker-hostname` argument to provide your externally routable IP or DNS name to SCOOP. You may as well be interested in the :option:`-e` argument for testing purposes.

Hostfile format
~~~~~~~~~~~~~~~

You can specify the hosts with a hostfile and pass it to SCOOP using the :option:`--hostfile` argument.
The hostfile should use the following syntax::

    hostname_or_ip 4
    other_hostname 5
    third_hostname 2

The name being the system hostname and the number being the number of workers
to launch on this host.

Using a list of host
~~~~~~~~~~~~~~~~~~~~

You can also use a list of host with the :option:`--host [...]` flag. In this
case, you must put every host separated by a space the number of time you wish
to have a worker on each of the node. For example::

    python -m scoop --host machine_a machine_a machine_b machine_b your_program.py

This example would start two workers on :option:`machine_a` and two workers on :option:`machine_b`.

Choosing the number of workers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The number of workers started should be equal to the number of cores you have 
on each machine. If you wish to start more or less workers than specified in your
hostfile or in your hostlist, you can use the :option:`-n` parameter.

.. note::
    The :option:`-n` parameter overrides any previously specified worker 
    amount.

    If :option:`-n` if less than the sum of workers specified in the hostfile
    or hostlist, the workers are launched in batch by host until the parameter
    is reached.
    This behavior may ignore latters hosts.

    If :option:`-n` if more than the sum of workers specified in the hostfile
    or hostlist, the remaining workers are distributed using a Round-Robin
    algorithm. Each host will increment its worker amount until the parameter
    is reached.

Be aware that tinkering with this parameter may hinder performances.
The default value choosen by SCOOP (one worker by physical core) is generaly a
good value.

Startup scripts (cluster or grid)
---------------------------------

You must provide a startup script on systems using a scheduler. Here are some
example startup scripts using different grid task managers. They
are available in the |submitFilesPath|_ directory.

.. |submitFilesPath| replace:: :file:`examples/submitFiles`
.. _submitFilesPath: https://code.google.com/p/scoop/source/browse/examples/submitFiles/

.. note::
    **Please note that these are only examples**. Refer to the documentation of 
    your scheduler for the list of arguments needed to run the task on your 
    grid or cluster.

Torque (Moab & Maui)
~~~~~~~~~~~~~~~~~~~~

Here is an example of a submit file for Torque:

.. literalinclude:: ../examples/submitFiles/Torque.sh

Sun Grid Engine (SGE)
~~~~~~~~~~~~~~~~~~~~~

Here is an example of a submit file for SGE:

.. literalinclude:: ../examples/submitFiles/SGE.sh

.. TODO Condor, Amazon EC2 using Boto & others


Pitfalls
--------

Program scope
~~~~~~~~~~~~~

As a good Python practice (see :pep:`395#what-s-in-a-name`), you should always 
wrap the executable part of your program using::

    if __name__ == '__main__':

This is mandatory when using parallel frameworks such as multiprocessing and 
SCOOP. Otherwise, each worker (or equivalent) will try to execute your code 
serially.

Also, only functions or classes declared at the top level of your program are
picklables. Here are some examples of non-working map invocations::

    # Script to be launched with: python -m scoop scriptName.py
    from scoop import futures


    class myClass(object):
        @staticmethod
        define myFunction(x):
            return x
    

    if __name__ == '__main__':
        define mySecondFunction(x):
            return x
        
        # Both of these calls won't work because Python pickle won't be able to
        # pickle or unpickle the function references.
        wrongCall1 = futures.map(myClass.myFunction, [1, 2, 3, 4, 5])
        wrongCall2 = futures.map(mySecondFunction, [1, 2, 3, 4, 5])

   
Evaluation laziness
~~~~~~~~~~~~~~~~~~~

The :meth:`~scoop.futures.map` and :meth:`~scoop.futures.submit` will distribute
their Futures both locally and remotely.
Futures executed locally will be computed upon access (iteration for the 
:meth:`~scoop.futures.map` and :meth:`~scoop._types.Future.result` for 
:meth:`~scoop.futures.submit`).Futures distributed remotely will be executed right away.

Large datasets
~~~~~~~~~~~~~~

Every parameter sent to a function by a :meth:`~scoop.futures.map` or 
:meth:`~scoop.futures.submit` gets serialized and sent within the Future to its
worker. It results in slow speeds and network overload when sending large
elements as a parameter to your function(s).

You should consider using a global variable in your module scope for passing
large elements; it will then be loaded on launch by every worker and won't
overload your network.

Incorrect::

    from scoop import futures


    def mySum(inData):
        """The worker will receive all its data from network."""
        return sum(inData)
    
    if __name__ == '__main__':
        data = [[i for i in range(x, x + 1000)] for x in range(0, 8001, 1000)]
        results = list(futures.map(mySum, data))

Better::

    from scoop import futures

    data = [[i for i in range(x, x + 1000)] for x in range(0, 8001, 1000)]


    def mySum(inIndex):
        """The worker will only receive an index from network."""
        return sum(data[inIndex])
    
    if __name__ == '__main__':
        results = list(futures.map(mySum, range(len(data))))
   
SCOOP and greenlets
~~~~~~~~~~~~~~~~~~~

.. warning::
    Since SCOOP uses greenlets to schedule and run futures. Programs that use 
    their own greenlets won't work with SCOOP. However, you should consider
    replacing the greenlets in your code by SCOOP functions.
