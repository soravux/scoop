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
This is an example usage of a mapScan function using SCOOP.
"""

from scoop import futures
import operator
from itertools import accumulate
import time

def manipulateData(inData):
    # Simulate a 10ms workload on every tasks
    time.sleep(0.01)
    return sum(inData)

if __name__ == '__main__':
    scoopTime = time.time()
    res = futures.mapScan(
        manipulateData,
        operator.add,
        list([a] * a for a in range(10))
    )
    scoopTime = time.time() - scoopTime
    print("Executed parallely in: {0:.3f}s with result: {1}".format(
        scoopTime,
        res
        )
    )

    serialTime = time.time()
    res = list(accumulate(map(manipulateData, list([a] * a for a in range(10)))))
    serialTime = time.time() - serialTime
    print("Executed serially in: {0:.3f}s with result: {1}".format(
        serialTime,
        res
        )
    )