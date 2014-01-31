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
A very simple example of recursive nested tasks.
Each task maps 2 others tasks, each of these 2 tasks maps 2 others, etc.,
up to RECURSIVITY_DEPTH.
"""

from scoop import futures

RECURSIVITY_DEPTH = 12

def recursiveFunc(level):
    if level == 0:
        return 1
    else:
        args = [level-1] * 2
        s = sum(futures.map(recursiveFunc, args))
        return s

if __name__ == "__main__":
    result = recursiveFunc(RECURSIVITY_DEPTH)
    print("2^{RECURSIVITY_DEPTH} = {result}".format(**locals()))
