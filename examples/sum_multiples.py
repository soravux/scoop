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
Sums the mutliples of 3 and 5 below 1000000
"""
from time import time
from scoop import futures
from operator import add

def multiples(n):
    return set(range(0, 1000000, n))


if __name__ == '__main__':
    bt = time()
    serial_result = sum(set.union(*map(multiples, [3, 5])))
    serial_time = time() - bt

    bt = time()
    parallel_result = sum(futures.mapReduce(multiples, set.union, [3, 5]))
    parallel_reduce_time = time() - bt

    assert serial_result == parallel_result

    print("Serial time: {0:.4f} s\nParallel time: {1:.4f} s"
          "".format(serial_time, parallel_reduce_time)
    )
