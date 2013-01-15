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
Computing a residual sum of squares using SCOOP.
"""

from __future__ import print_function
import random
import operator
import time
from scoop import futures

# The data is generated on every workers for the sake of this example.
# This data could come from a file located on a shared hard drive or else.
random.seed(31415926)
leftSignal = [random.randint(-100, 100) for _ in range(200000)]
rightSignal = [random.randint(-100, 100) for _ in range(200000)]

# Set the size of each worker batch
PARALLEL_SIZE = 25000

# Set the parallel function that will compute the Residual Sum of Squares
# The index represent the element 
def RSS(index):
    data = zip(leftSignal[index:index+PARALLEL_SIZE],
               rightSignal[index:index+PARALLEL_SIZE])
    return sum(abs(a - b)**2 for a, b in data)

if __name__ == "__main__":
    # Parallel with reduction call
    ts = time.time()
    prresult = futures.mapReduce(RSS,
                                 operator.add,
                                 range(0, len(leftSignal), PARALLEL_SIZE))
    prtime = time.time() - ts
    print("mapReduce result obtained in {0:03f}s".format(prtime))

    # Parallel call. This should get approximatively the same time as with
    # reduction because the reduction is instant with this amount of data.
    ts = time.time()
    presult = sum(futures.map(RSS,
                              range(0, len(leftSignal), PARALLEL_SIZE)))
    ptime = time.time() - ts
    print("map result obtained in {0:03f}s".format(prtime))

    # Serial
    ts = time.time()
    sresult = sum(abs(a - b)**2 for a, b in zip(leftSignal, rightSignal))
    stime = time.time() - ts
    print("Serial result obtained in {0:03f}s".format(stime))
    assert prresult == presult == sresult
