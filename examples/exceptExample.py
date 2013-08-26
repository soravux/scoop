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
A simple example to show some case of exception handling using Scoop. The exception
handling are done in the same way as they are in python. However, exception dealt
by Scoop using python3 are a lot more clear than if python2 was used.
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
    try:
        # The map alone doesn't throw the exception. The exception is raised
        # in the sum which calls the map generator.
        result = sum(futures.map(func2, [i+1 for i in range(n)]))
    except Exception as err:
        # We could do some stuff here
        raise Exception("This exception is normal")
    return result

def func2(n):
    if n > 10:
        # This exception is treated in func1
        raise Exception(10)
    launches = []
    for i in range(n):
        launches.append(futures.submit(func3, i + 1))
    result = futures.as_completed(launches)
    return sum(res.result() for res in result)

def func3(n):
    result = []
    try:
        result = list(futures.map(func4, [i+1 for i in range(n)]))
    except Exception as e:
        # We return what we can
        return e.args[0] + sum(result)
    # No exception was generated
    return sum(result)

def func4(n):
    result = n*n
    if result > 20:
        # This exception is treated in func3
        raise Exception(result)
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
