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
Shows the conditional execution of a parallel Future.
"""
from scoop import futures
import random

first_type = lambda x: x + " World"
second_type = lambda x: x + " Parallel World"

if __name__ == '__main__':
    if random.random() < 0.5:
        my_future = futures.submit(first_type, "Hello")
    else:
        my_future = futures.submit(second_type, "Hello")
    print(my_future.result())
