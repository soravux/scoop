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
    task = futures.submit(func1, n)
    result = futures.join(task)
    return result

def func1(n):
    result = futures.mapJoin(func2, [i+1 for i in range(0,n)])
    return sum(result)

def func2(n):
    result = futures.mapJoin(func3, [i+1 for i in range(0,n)])
    return sum(result)

def func3(n):
    result = futures.mapJoin(func4, [i+1 for i in range(0,n)])
    return sum(result)

def func4(n):
    result = n*n
    return result

def main():
    task = futures.submit(func0, 20)
    result = futures.join(task)
    print(result)
    return result

if __name__ == "__main__":
    futures.startup(main)