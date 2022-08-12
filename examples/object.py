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
Example of dynamic parallel object manipulation.
"""
from scoop import futures


class myClass(object):
    """An object with an instance variable."""
    def __init__(self):
        self.myVar = 5


def modifyClass(myInstance):
    """Function modifying an instance variable."""
    myInstance.myVar += 1
    return myInstance


def main():
    # Create object instances
    myInstances = [myClass() for _ in range(20)]
    # Modify them parallelly
    myAnswers = list(futures.map(modifyClass, myInstances))

    # Each result is a new object with the modifications applied
    print(myAnswers)
    print([a.myVar for a in myAnswers])


if __name__ == "__main__":
    main()
