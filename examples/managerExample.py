#
#    This file is part of Scalable COncurrent Operations in Python (SCOOP).
#
#    SCOOP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    SCOOP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with SCOOP. If not, see <http://www.gnu.org/licenses/>.
#
"""
Example of manager use
"""

from math import hypot
from random import random
from scoop import futures, manager
from time import time

# A range is used in this function for python3. If you are using python2, a
# xrange might be more efficient.
def test(tries):
    print("Data in shared variables: ", manager.Manager.elements)
    return sum(hypot(random(), random()) < 1 for _ in range(tries))


# Calculates pi with a Monte-Carlo method. This function calls the function
# test "n" times with an argument of "t". Scoop dispatches these 
# functions interactively accross the available ressources.
def calcPi(workers, tries):
    bt = time()
    expr = futures.map(test, [tries] * workers)
    piValue = 4. * sum(expr) / float(workers * tries)
    totalTime = time() - bt
    print("pi = " + str(piValue))
    print("total time: " + str(totalTime))
    return piValue

if __name__ == "__main__":
    myManager = manager.Manager()
    myManager['myVar'] = {1: 'Test1',
                          2: 'Test2',
                          3: 'Test3',
                          4: 'Test4',
                          5: 'Test5',
                          6: 'Test6',
                          7: 'Test7',
                         }
    myManager['secondVar'] = "Hello World!"
    # TODO: This could be interesting
    #myManager['remoteExec'] = test
    dataPi = calcPi(10, 5000)
