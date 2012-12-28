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
from functools import reduce
from . import encapsulation

elements = None


def ensureAtomicity(fn):
    def wrapper(*args, **kwargs):
        # TODO: Import that elsewhere
        from . import _control

        # Enforce retrieval of currently awaiting constants
        _control.execQueue.socket.pumpInfoSocket()

        for key, value in kwargs.items():
            # Object name existence check
            if key in itertools.chain(*(elem.keys() for elem in elements.values())):
                raise TypeError("This constant already exists: {0}.".format(key))
            
        # Call the function
        fn(*args, **kwargs)

        # Wait for element propagation
        import time
        import scoop
        while all(key in elements[scoop.worker] for key in kwargs.keys()) is not True:
            # Enforce retrieval of currently awaiting constants
            _control.execQueue.socket.pumpInfoSocket()
            # TODO: Make previous blocking instead of sleep
            time.sleep(0.1)

        # Atomicity check
        elementNames = list(itertools.chain(*(elem.keys() for elem in elements.values())))
        if len(elementNames) != len(set(elementNames)):
            raise TypeError("This constant already exists: {0}.".format(key))

    return wrapper


@ensureAtomicity
def shareConstant(**kwargs):
    # TODO: Import that elsewhere
    from . import _control
    
    sendVariable = _control.execQueue.socket.sendVariable

    for key, value in kwargs.items():
        # Propagate the constant
        if hasattr(value, '__code__'):
            sendVariable(key, encapsulation.FunctionEncapsulation(value))
        # TODO: file-like objects with encapsulation.ExternalEncapsulation
        else:
            sendVariable(key, value)

def getConstant(key):
    # TODO: Import that elsewhere
    from . import _control

    # Enforce retrieval of currently awaiting constants
    _control.execQueue.socket.pumpInfoSocket()

    # TODO: Wait for propagation
    constants = dict(reduce(lambda x, y: list(x.items()) + list(y.items()),
                            elements.values(),
                            []))
    return constants.get(key)