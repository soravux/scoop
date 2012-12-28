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
Example of shared constants use.
This example is based on the piCalc example.
"""
from scoop import futures, shared
from time import time
import scoop

# A range is used in this function for python3. If you are using python2, a
# xrange might be more efficient.
def test(tries):
    from math import hypot
    from random import random

    # Examples of function and constant retrieval
    myRemoteFonc = shared.getConstant('mySharedFunction')
    myRemoteFonc('Example Parameter')
    print(shared.getConstant('myVar')[2])

    # Monte-Carlo evaluation
    return sum(hypot(random(), random()) < 1 for _ in range(tries))


# Calculates pi with a Monte-Carlo method. This function calls the function
# test "n" times with an argument of "t". SCOOP dispatches these 
# functions interactively accross the available ressources.
def calcPi(workers, tries):
    bt = time()
    # Evaluation function retrieval at runtime
    piCalcTestFunction = shared.getConstant('piCalcTestFunction')
    expr = futures.map(piCalcTestFunction, [tries] * workers)
    piValue = 4. * sum(expr) / float(workers * tries)
    totalTime = time() - bt
    print("pi = " + str(piValue))
    print("total time: " + str(totalTime))
    return piValue


def myFunc(parameter):
    print('Hello World from {0}!'.format(scoop.worker))
    print(parameter)


class exampleClass(object):
    pass


if __name__ == "__main__":
    shared.shareConstant(myVar={1: 'First element',
                                2: 'Second element',
                                3: 'Third element',
                               })
    shared.shareConstant(secondVar="Hello World!")
    shared.shareConstant(mySharedFunction=myFunc)
    shared.shareConstant(piCalcTestFunction=test)
    
    # Un-commenting the following line will give a TypeError
    #shared.shareConstant(myVar="Variable re-assignation")
    dataPi = calcPi(10, 5000)
