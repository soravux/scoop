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
SCOOP also works on lambda functions even if they aren't picklable by default.
"""
from scoop import futures, shared
from math import cos
import operator


if __name__ == "__main__":
    # Standard lambda function
    myFunc = lambda x: x * 2
    # Lambda function using a globally defined function
    myFunc2 = lambda x: cos(x)
    # Lambda function using a function through a module definition
    myFunc3 = lambda x: operator.add(x, 1)

    # Calls to SCOOP
    print(list(futures.map(myFunc, range(10))))
    print(list(futures.map(myFunc2, range(10))))
    print(list(futures.map(myFunc3, range(10))))

