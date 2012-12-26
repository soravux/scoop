#!/usr/bin/env python
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

import itertools

elements = None


def shareConstant(**kwargs):
    # TODO: Import that elsewhere
    from . import _control

    # Enforce retrieval of currently awaiting constants
    _control.execQueue.socket.pumpInfoSocket()

    for key, value in kwargs.items():
        # Sanity check
        if key in itertools.chain(*(elem.keys() for elem in elements.values())):
            raise TypeError("This constant already exists: {0}.".format(key))

        # Propagate the constant
        # TODO: atomicity
        _control.execQueue.socket.sendVariable({key: value})

    import time
    import scoop
    while all(key in elements[scoop.worker] for key in kwargs.keys()) is not True:
        # Enforce retrieval of currently awaiting constants
        _control.execQueue.socket.pumpInfoSocket()
        # TODO: Make previous blocking instead of sleep
        time.sleep(0.1)


def getConstant(key):
    # TODO: Import that elsewhere
    from . import _control

    # Enforce retrieval of currently awaiting constants
    _control.execQueue.socket.pumpInfoSocket()
    return elements.get(key)