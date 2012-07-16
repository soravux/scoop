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
A simple example showing how to resolve a full balanced tree with multiples
techniques using SCOOP.
"""
from __future__ import print_function
from scoop import futures

def func0(n):
    # Task submission is asynchronous; It will return immediately.
    task = futures.submit(func1, n)
    # The call blocks here until it gets the result
    result = task.result()
    return result

def func1(n):
    # This call results in a generator function
    result = futures.map(func2, [i+1 for i in range(n)])
    # The results get evaluated here when they are accessed here
    return sum(result)

def func2(n):
    launches = [futures.submit(func3, i + 1) for i in range(n)]
    # Spawn a generator for each completion, unordered
    result = [a.result() for a in futures.as_completed(launches)]
    return sum(result)

def func3(n):
    # To force an immediate evaluation, you can wrap your map in a list such as:
    result = list(futures.map(func4, [i+1 for i in range(n)]))
    return sum(result)

def func4(n):
    result = n*n
    return result

def main():
    task = futures.submit(func0, 20)
    # You can wait for a result before continuing computing
    futures.wait([task], return_when=futures.ALL_COMPLETED)
    result = task.result()
    print(result)
    return result

if __name__ == "__main__":
    main()