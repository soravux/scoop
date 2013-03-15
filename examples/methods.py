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
SCOOP also works on methods even if they aren't picklable by default.
Note that this will correctly propagate the internal state of its instance.
"""
from scoop import futures, shared


class MyClass(object):
    def myMethod(self, x):
        return x * 2


if __name__ == "__main__":
    a = MyClass()
    print(list(futures.map(a.myMethod, range(10))))
