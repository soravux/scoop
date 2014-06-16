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
Shows the usage of the map_as_completed() function
"""
from scoop import futures


def hello(input_):
    return input_


if __name__ == "__main__":
    print("Execution of map():")
    # Example of how to use a normal map function
    for out in futures.map(hello, range(10)):
        print("Hello from #{}!".format(out))

    print("Execution of map_as_completed():")
    # Example of map_as_completed usage. Note that the results won't necessarily be ordered
    # like the previous 
    for out in futures.map_as_completed(hello, range(10)):
        print("Hello from #{}!".format(out))
