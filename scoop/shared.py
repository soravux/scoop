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
import time

elements = None


def _ensureAtomicity(fn):
    """Ensure atomicity of passed elements on the whole worker pool"""
    def wrapper(*args, **kwargs):
        """setConst(**kwargs)
        Set a constant that will be shared to every workers.

        :param **kwargs: One or more combination(s) key=value. Key being the
            variable name and value the object to share.

        :returns: None.

        Usage: setConst(name=value)
        """
        # Note that the docstring is the one of setConst. This is because of
        # sphinx.

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


@_ensureAtomicity
def setConst(**kwargs):
    """setConst(**kwargs)
    Set a constant that will be shared to every workers.

    :param **kwargs: One or more combination(s) key=value. Key being the
        variable name and value the object to share.

    :returns: None.

    Usage: setConst(name=value)
    """
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

def getConst(name, timeout=0.1):
    """Get a constant that was shared beforehand.

    :param name: The name of the shared variable to retrieve.
    :param timeout: The maximum time to wait for the propagation of the
        variable.

    :returns: The shared object.

    Usage: value = getConst('name')
    """
    # TODO: Import that elsewhere
    from . import _control
    import time

    timeStamp = time.time()
    while True:
        # Enforce retrieval of currently awaiting constants
        _control.execQueue.socket.pumpInfoSocket()

        # Constants concatenation
        constants = dict(reduce(lambda x, y: x + list(y.items()),
                                elements.values(),
                                []))
        timeoutHappened = time.time() - timeStamp > timeout
        if constants.get(name) is not None or timeoutHappened:
            return constants.get(name)
        time.sleep(0.01)