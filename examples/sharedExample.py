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
Example of shared constants use.
This syntetic example only showcase the shared module API.
"""
from scoop import futures, shared
# Import SCOOP to get access to its constants such as scoop.worker
import scoop


def myFunc(parameter):
    """This function will be executed on the remote host even if it was not
       available at launch."""
    print('Hello World from {0}!'.format(scoop.worker))

    # It is possible to get a constant anywhere
    print(shared.getConst('myVar')[2])

    # Parameters are handled as usual
    return parameter + 1


if __name__ == "__main__":
    # Populate the shared constants
    shared.setConst(myVar={1: 'First element',
                                2: 'Second element',
                                3: 'Third element',
                               })
    shared.setConst(secondVar="Hello World!")
    shared.setConst(myFunc=myFunc)

    # Use the previously defined shared function
    print(list(futures.map(myFunc, range(10))))
    
    # Un-commenting the following line will give a TypeError
    # since re-defining a constant is not allowed.
    #shared.setConst(myVar="Variable re-assignation")
