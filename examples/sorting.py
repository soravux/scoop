#!/usr/bin/env python
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
"""Parallel merge sorting example using the futures"""
import sys
import time
import random

from scoop import futures, shared
from itertools import repeat


def merge(left, right):
    result = []
    i, j = 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result += left[i:]
    result += right[j:]
    return result


def mergesort(lst, current_depth=0, parallel_depth=0):
    if len(lst) <= 1:
        return lst
    middle = int(len(lst) / 2)
    if current_depth < parallel_depth:
        results = list(
            futures.map(
                mergesort,
                [
                    lst[:middle],
                    lst[middle:],
                ],
                repeat(current_depth+1),
                repeat(parallel_depth),
            )
        )
    else:
        results = []
        results.append(mergesort(lst[:middle]))
        results.append(mergesort(lst[middle:]))
    return merge(*results)


if __name__ == "__main__":
    the_list = [random.randint(-sys.maxsize - 1, sys.maxsize) for r in range(10000)]
    shared.setConst(the_list=the_list)

    ts = time.time()
    parallel_result = mergesort(the_list, parallel_depth=1)
    pts = time.time() - ts

    ts = time.time()
    serial_result = mergesort(the_list)
    sts = time.time() - ts
    
    print("Parallel time: {0:.5f}s".format(pts))
    print("Serial time:   {0:.5f}s".format(sts))

    assert serial_result == parallel_result
