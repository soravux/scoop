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
Calculation of Pi using a Monte Carlo method. This version is used in the 
documentation and should be kept as clean as possible for study purposes.
"""

from math import hypot
from random import random
from scoop import futures

def test(tries):
    return sum(hypot(random(), random()) < 1 for i in range(tries))

def calcPi(nbFutures, tries):
    expr = futures.map(test, [tries] * nbFutures)
    return 4. * sum(expr) / float(nbFutures * tries)

if __name__ == "__main__":
    print("pi = {}".format(calcPi(3000, 5000)))
