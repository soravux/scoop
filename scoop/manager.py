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


class Manager(object):
    """Variable passing interface"""
    # Shared variables containing {workerID:{varName:varVal},}
    # Will be initialized by the broker
    elements = None

    def __getitem__(self, key):
        # Enforce retrieval of currently awaiting variables
        _control.execQueue.socket.pumpInfoSocket()
        return Manager.elements.get(key)

    def __setitem__(self, key, value):
        # TODO: Import that elsewhere
        from . import _control
        # if value == None, remove from dictionary
        _control.execQueue.socket.sendVariable({key: value})