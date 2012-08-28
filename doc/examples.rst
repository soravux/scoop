Examples
========

You can find the examples detailed on this page in the |exampleDirectory|_
directory of SCOOP.

.. |exampleDirectory| replace:: :file:`examples/`
.. _exampleDirectory: https://code.google.com/p/scoop/source/browse/examples/

Please check the :doc:`api` for any implentation detail of the proposed 
functions.


Computation of :math:`\pi`
--------------------------

A `Monte-Carlo method <http://en.wikipedia.org/wiki/Monte_Carlo_method>`_ to 
calculate :math:`\pi` using SCOOP to parallelize its computation is found in 
|piCalcFile|_.
You should familiarize yourself with 
`Monte-Carlo methods <http://en.wikipedia.org/wiki/Monte_Carlo_method>`_ before
going forth with this example. 

.. figure:: images/monteCarloPiExample.gif
    :align: right
    :height: 300px
    :width: 300px
    :figwidth: 300px
    :alt: Monte Carlo computation of Pi.

    Image from `Wikipedia <http://en.wikipedia.org/wiki/Monte_Carlo_method>`_
    made by `CaitlinJo <http://commons.wikimedia.org/wiki/User:CaitlinJo>`_
    that shows the Monte Carlo computation of :math:`\pi`.

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
one is produced (red dots in the figure), otherwise the value is zero (blue dots
in the figure).
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
---------------

The |fullTreeFile|_ example holds a pretty good wrap-up of available
functionnalities.
It notably shows that SCOOP is capable of handling twisted and complex
hierarchical requirements.

.. |fullTreeFile| replace:: :file:`examples/fullTree.py`
.. _fullTreeFile: https://code.google.com/p/scoop/source/browse/examples/fullTree.py

Getting acquainted with the previous examples is fairly enough to use SCOOP, no
need to dive into this complicated example.
