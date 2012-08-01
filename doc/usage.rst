Usage
=====

Nomenclature
------------

.. _Nomenclature-table:

=========== =======================================================================================================================================
  Keyword   Description
=========== =======================================================================================================================================
Future(s)   The Future class encapsulates the asynchronous execution of a callable (Previously referred to as `task`).
Broker      Dispatch Futures.
Worker      Process executing Futures.
Origin      The worker executing the user program.
=========== =======================================================================================================================================

Architecture diagram
--------------------

The future(s) distribution over workers is done by a 
`Broker pattern <http://zguide.zeromq.org/page:all#A-Request-Reply-Broker>`_. 
In such pattern, workers act as independant elements which interacts with a 
broker to mediate their communications.

.. image:: images/architecture.png
   :align: center

How to use SCOOP in your code
-----------------------------

The philosophy of SCOOP is loosely built around the *futures* module proposed 
by :pep:`3148`. It primarily defines a :meth:`~scoop.futures.map` and a 
:meth:`~scoop.futures.submit` function allowing asynchroneous computation which 
SCOOP will propagate to its workers. 

Map
~~~

A |map()|_ function applies multiple parameters to a single function. For 
example, if you want to apply the |abs()|_ function to every number of a list::

    import random
    data = [random.randint(-1000,1000) for r in range(10000)]
    
    # Without Map
    result = []
    for i in range(len(data)):
      result.append(abs(data[i]))

    # Using a Map
    result = list(map(abs, data))

.. |abs()| replace:: *abs()*
.. _abs(): http://docs.python.org/library/functions.html#abs

SCOOP's :meth:`~scoop.futures.map` returns a generator over the results 
in-order. It can thus act as a parallel substitute to the standard |map()|_, for
instance::

    # Script to be launched with: python -m scoop scriptName.py
    import random
    from scoop import futures
    data = [random.randint(-1000,1000) for r in range(2**16)]

    if __name__ == '__main__':
        # Python's standard serial function
        dataSerial = list(map(abs, data))

        # SCOOP's parallel function
        dataParallel = list(futures.map(abs, data))

        assert dataSerial == dataParallel

.. |map()| replace:: *map()*
.. _map(): http://docs.python.org/library/functions.html#map

.. _test-for-main-mandatory:

.. note::
    You *must* wrap your code with a test for the __main__ name as show above.
    Failure to do so will result in every worker trying to run their own 
    instance of the program. This ensures that every worker waits for 
    parallelized tasks spawned by the origin worker.

Submit
~~~~~~

SCOOP's :meth:`~scoop.futures.submit` returns a :class:`~scoop._types.Future` 
instance. 
This allows a finer control over the Futures, such as out-of-order processing.

.. _examples-reference:

Examples
--------
    
Examples are available in the |exampleDirectory|_ directory of scoop. 

.. |exampleDirectory| replace:: :file:`examples/`
.. _exampleDirectory: https://code.google.com/p/scoop/source/browse/examples/

Computation of :math:`\pi`
~~~~~~~~~~~~~~~~~~~~~~~~~~

A `Monte-Carlo method <http://en.wikipedia.org/wiki/Monte_Carlo_method>`_ to 
calculate :math:`\pi` using SCOOP to parallelize its computation is found in 
|piCalcFile|_.
You should familiarize yourself with 
`Monte-Carlo methods <http://en.wikipedia.org/wiki/Monte_Carlo_method>`_ before
going forth with this example. 

.. |piCalcFile| replace:: :file:`examples/piCalc.py`
.. _piCalcFile: https://code.google.com/p/scoop/source/browse/examples/piCalc.py

First, we need to import the needed functions as such:

.. literalinclude:: ../examples/piCalcDoc.py
   :lines: 22-24
   :linenos:

The `Monte-Carlo method <http://en.wikipedia.org/wiki/Monte_Carlo_method>`_ is
then defined. It spawns two pseudo-random numbers that are fed to the 
`hypot <http://docs.python.org/library/math.html#math.hypot>`_ function which 
calculates the hypotenuse of its parameters.
This step computes the 
`Pythagorean equation <http://en.wikipedia.org/wiki/Pythagorean_theorem>`_
(:math:`\sqrt{x^2+y^2}`) of the given parameters to find the distance from the 
origin (0,0) to the randomly placed point (which X and Y values were generated 
from the two pseudo-random values).
Then, the result is compared to one to evaluate if this point is inside or 
outside the `unit disk <http://en.wikipedia.org/wiki/Unit_disk>`_.
If it is inside (have a distance from the origin lesser than one), a value of 
one is produced, otherwise the value is zero.
The experiment is repeated ``tries`` number of times with new random values.

The function returns the number times a pseudo-randomly generated point fell
inside the `unit disk <http://en.wikipedia.org/wiki/Unit_disk>`_ for a given
number of tries.

.. TODO: don't restart line numbering

.. literalinclude:: ../examples/piCalcDoc.py
   :lines: 26-27
   :linenos:

One way to obtain a more precise result with a 
`Monte-Carlo method <http://en.wikipedia.org/wiki/Monte_Carlo_method>`_ is to
perform the method multiple times. The following function executes repeatedly
the previous function to gain more precision.
These calls are handled by SCOOP using it's :meth:`~scoop.futures.map` 
function.
The results, that is the number of times a random distribution over a 1x1 
square hits the `unit disk <http://en.wikipedia.org/wiki/Unit_disk>`_ over a 
given number of tries, are then summed and divided by the total of tries.
Since we only covered the upper right quadrant of the
`unit disk <http://en.wikipedia.org/wiki/Unit_disk>`_ because both parameters
are positive in a cartesian map, the result must be multiplied by 4 to get the 
relation between area and circumference, namely 
:math:`\pi`.

.. literalinclude:: ../examples/piCalcDoc.py
   :lines: 29-31
   :linenos:

As :ref:`stated above <test-for-main-mandatory>`, you `must` wrap your code with a test for the __main__ name.
You can now run your code using the command :program:`python -m scoop`.

.. literalinclude:: ../examples/piCalcDoc.py
   :lines: 33-34
   :linenos:

Overall example
~~~~~~~~~~~~~~~

The |fullTreeFile|_ example holds a pretty good wrap-up of available
functionnalities:

.. TODO: Document it like piCalc.

.. |fullTreeFile| replace:: :file:`examples/fullTree.py`
.. _fullTreeFile: https://code.google.com/p/scoop/source/browse/examples/fullTree.py

.. literalinclude:: ../examples/fullTree.py
   :lines: 22-
    
Please check the :doc:`api` for any implentation detail of the proposed 
functions.

How to launch SCOOP programs
----------------------------

The scoop module spawns the needed broker and workers on a given list of 
computers, including remote ones via :program:`ssh`.

Programs using SCOOP need to be launched with the :option:`-m scoop` parameter 
passed to Python, as such::
    
    cd scoop/examples/
    python -m scoop fullTree.py

.. note::
  If you are using a Python version prior to 2.7, you must start SCOOP using 
  :option:`-m scoop.__main__`. You should also consider using an up-to-date 
  version of Python.
    
Here is a list of the parameters that can be passed to scoop::

    python -m scoop --help
    usage: python -m scoop [-h]
                           [--hosts [HOSTS [HOSTS ...]] | --hostfile HOSTFILE]
                           [--path PATH] [--nice NICE]
                           [--verbose] [--log LOG] [-n N]
                           [-e] [--broker-hostname BROKER_HOSTNAME]
                           [--python-executable PYTHON_EXECUTABLE]
                           [--pythonpath PYTHONPATH] [--debug]
                           executable ...

    Starts a parallel program using SCOOP.

    positional arguments:
      executable            The executable to start with SCOOP
      args                  The arguments to pass to the executable

    optional arguments:
      -h, --help            show this help message and exit
      --hosts [HOSTS [HOSTS ...]], --host [HOSTS [HOSTS ...]]
                            The list of hosts. The first host will execute the
                            origin. (default is 127.0.0.1)
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

      --debug               Turn on the debuging

A remote workers example may be as follow::

    python -m scoop --hostfile hosts -vv -n 6 your_program.py [your arguments]

================    =================================
Argument            Meaning
================    =================================
-m scoop            **Mandatory** Uses SCOOP to run program.
--hostfile          hosts is a file containing a list of host to launch scoop
-vv                 Double verbosity flag.
-n 6                Launch a total of 6 workers.
your_program.py     The program to be launched.
[your arguments]    The arguments that needs to be passed to your program.
================    =================================

.. note::
    Your local hostname must be externally routable for remote hosts to be able to connect to it. If you don't have a DNS properly set up on your local network or a system hosts file, consider using the :option:`--broker-hostname` argument to provide your externally routable IP or DNS name to SCOOP. You may as well be interested in the :option:`-e` argument for testing purposes.

Hostfile format
~~~~~~~~~~~~~~~

.. TODO: slots inevitable?

You should create a hostfile and pass it to SCOOP using the :option:`--hostfile` argument.
The hostfile should use the following syntax::

    hostname_or_ip workers=4
    other_hostname workers=5
    third_hostname workers=2

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
on each machine. The easiest way to specify the number of workers started is
by making a hostfile. If you wish to start more or less worker than specified in your
hostfile or in your hostlist, you can use the flag :option:`-n`.
You should be carefull not to start to much worker as this can cause performances limitation.
The default value of one worker by physical core is generaly a good value.

Startup scripts (supercomputer or grid)
---------------------------------------

You must provide a startup script on systems using a scheduler. Here is 
provided some example startup scripts using different grid task managers. They
are available in the |submitFilesPath|_ directory.

.. |submitFilesPath| replace:: :file:`examples/submitFiles`
.. _submitFilesPath: https://code.google.com/p/scoop/source/browse/examples/submitFiles/

.. note::
    **Please note that these are only examples**. Refer to the documentation of 
    your scheduler for the list of arguments needed to run the task on your 
    grid.

Torque (Moab & Maui)
~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for Torque:

.. literalinclude:: ../examples/submitFiles/Torque.sh

Sun Grid Engine (SGE)
~~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for SGE:

.. literalinclude:: ../examples/submitFiles/SGE.sh

.. TODO Condor, Amazon EC2 using Boto & others
        ~~~~~~

Pitfalls
--------

.. * (Global variables? Todo?)

Program scope
~~~~~~~~~~~~~

As a good Python practice (see :pep:`395#what-s-in-a-name`), you should always 
wrap the executable part of your program using::

    if __name__ == '__main__':

This is mandatory when using parallel frameworks such as multiprocessing and 
SCOOP. Otherwise, each worker (or equivalent) will try to execute your code 
serially.
   
Evaluation laziness
~~~~~~~~~~~~~~~~~~~

The :meth:`~scoop.futures.map` and :meth:`~scoop.futures.submit` will distribute
their Futures both locally and remotely.
Futures executed locally will be computed upon access (iteration for the 
:meth:`~scoop.futures.map` and :meth:`~scoop._types.Future.result` for 
:meth:`~scoop.futures.submit`).
Futures distributed remotely will be executed right away.

Large datasets
~~~~~~~~~~~~~~

Every parameter sent to a function by a :meth:`~scoop.futures.map` or 
:meth:`~scoop.futures.submit` gets serialized and sent within the Future to its
worker. Consider using a global variable in your module scope for passing large
elements; it will then be loaded on launch by every worker and won't overload
your network.

Incorrect::

    from scoop import futures
    
    if __name__ == '__main__':
        results = list(futures.map(sum, zip(*([range(8)])*(2**16))))

Better::

    from scoop import futures

    data = [[i for i in range(x, x + 1000)] for x in range(0, 8001, 1000)]


    def mySum(inIndex):
      return sum(data[inIndex])
    
    if __name__ == '__main__':
        results = list(futures.map(mySum, range(8)))
   
SCOOP and greenlets
~~~~~~~~~~~~~~~~~~~

Since SCOOP uses greenlets to schedule and run futures, programs using 
greenlets won't work with SCOOP. However, you should consider replacing 
the greenlets in your code by SCOOP functions.
