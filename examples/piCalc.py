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
Calculation of Pi using a Monte Carlo method.
"""

from math import hypot
from random import random
from scoop import futures
from time import time

# A range is used in this function for python3. If you are using python2, a
# xrange might be more efficient.
def test(tries):
    return sum(hypot(random(), random()) < 1 for i in range(tries))

def calcPi(n, t):
    bt = time()
    expr = futures.map(test, [t] * n)
    pi_value = 4. * sum(expr) / float(n*t)
    totalTime = time() - bt
    print("pi = " + str(pi_value))
    print("total time {}".format(totalTime))
    return pi_value

if __name__ == "__main__":
    dataPi = calcPi(3000, 5000)

