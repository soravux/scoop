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
Shows how to develop a program working with or without scoop launched
providing serial map fallback. This example works even if SCOOP isn't
installed.
"""
try:
    import scoop
    if scoop.is_running:
        from scoop.futures import map as map_
    else:
        raise ImportError()
except ImportError:
    map_ = map

def helloWorld(value):
    return "Hello World from Future #{0}".format(value)

if __name__ == "__main__":
    returnValues = list(map_(helloWorld, range(16)))
    print("\n".join(returnValues))
