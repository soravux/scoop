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
from inspect import ismethod
from functools import reduce
import time

from . import encapsulation, utils
import scoop
from .fallbacks import ensureScoopStartedProperly, NotStartedProperly


elements = None


def _ensureAtomicity(fn):
    """Ensure atomicity of passed elements on the whole worker pool"""
    @ensureScoopStartedProperly
    def wrapper(*args, **kwargs):
        """setConst(**kwargs)
        Set a constant that will be shared to every workers.
        This call blocks until the constant has propagated to at least one
        worker.

        :param \*\*kwargs: One or more combination(s) key=value. Key being the
            variable name and value the object to share.

        :returns: None.

        Usage: setConst(name=value)
        """
        # Note that the docstring is the one of setConst.
        # This is because of the documentation framework (sphinx) limitations.

        from . import _control

        # Enforce retrieval of currently awaiting constants
        _control.execQueue.socket.pumpInfoSocket()

        for key, value in kwargs.items():
            # Object name existence check
            if key in itertools.chain(*(elem.keys() for elem in elements.values())):
                raise TypeError("This constant already exists: {0}.".format(key))

        # Retry element propagation until it is returned
        while all(key in elements.get(scoop.worker, []) for key in kwargs.keys()) is not True:
            scoop.logger.debug("Sending global variables {0}...".format(
                list(kwargs.keys())
            ))
            # Call the function
            fn(*args, **kwargs)

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
    from . import _control
    
    sendVariable = _control.execQueue.socket.sendVariable

    for key, value in kwargs.items():
        # Propagate the constant
        # for file-like objects, see encapsulation.py where copyreg was
        # used to overload standard pickling.
        if callable(value):
            sendVariable(key, encapsulation.FunctionEncapsulation(value, key))
        else:
            sendVariable(key, value)


def getConst(name, timeout=0.1):
    """Get a shared constant.

    :param name: The name of the shared variable to retrieve.
    :param timeout: The maximum time to wait in seconds for the propagation of
        the constant.

    :returns: The shared object.

    Usage: value = getConst('name')
    """
    from . import _control
    import time

    timeStamp = time.time()
    while True:
        # Enforce retrieval of currently awaiting constants
        _control.execQueue.socket.pumpInfoSocket()

        # Constants concatenation
        constants = dict(reduce(
            lambda x, y: x + list(y.items()),
            elements.values(),
            []
        ))
        timeoutHappened = time.time() - timeStamp > timeout
        if constants.get(name) is not None or timeoutHappened:
            return constants.get(name)
        time.sleep(0.01)


class SharedElementEncapsulation(object):
    """Encapsulates a reference to an element available in the shared module.

    This is used by Futures (map on lambda, for instance)."""
    def __init__(self, element):
        self.isMethod = False
        if utils.isStr(element):
            # Already shared element
            assert getConst(element, timeout=0) != None, (
                "Element must already be shared."
            )
            self.uniqueID = element
        else:
            # Element to share
            # Determine if function is a method. Methods derived from external
            # languages such as C++ aren't detected by ismethod.
            if ismethod(element):
                # Must share whole object before ability to use its method
                self.isMethod = True
                self.methodName = element.__name__
                element = element.__self__

            # Lambda-like or unshared code to share
            uniqueID = str(scoop.worker) + str(id(element)) + str(hash(element))
            self.uniqueID = uniqueID
            if getConst(uniqueID, timeout=0) == None:
                funcRef = {uniqueID: element}
                setConst(**funcRef)

    def __repr__(self):
        return self.uniqueID

    def __call__(self, *args, **kwargs):
        if self.isMethod:
            wholeObj = getConst(
                self.__repr__(),
                timeout=float("inf"),
            )
            return getattr(wholeObj, self.methodName)(*args, **kwargs)
        else:
            return getConst(self.__repr__(),
                            timeout=float("inf"))(*args, **kwargs)

    def __name__(self):
        return self.__repr__()
