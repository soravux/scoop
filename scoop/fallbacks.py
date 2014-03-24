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
"""Module containing builins fallbacks or exceptions when SCOOP is not
started properly."""
import sys
import warnings
from functools import wraps


class NotStartedProperly(Exception):
    """SCOOP was not started properly"""
    pass


def ensureScoopStartedProperlyMapFallback(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        futures_not_loaded = 'scoop.futures' not in sys.modules
        controller_not_started = not (
            sys.modules['scoop.futures'].__dict__.get("_controller", None)
        )
        if futures_not_loaded or controller_not_started:
            if not hasattr(ensureScoopStartedProperlyMapFallback, "already"):
                warnings.warn(
                    "SCOOP was not started properly.\n"
                    "Be sure to start your program with the "
                    "'-m scoop' parameter. You can find "
                    "further information in the "
                    "documentation.\n"
                    "Your map call has been replaced by the builtin "
                    "serial Python map().",
                    RuntimeWarning
                )
                ensureScoopStartedProperlyMapFallback.already = True
            return map(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


def ensureScoopStartedProperly(func):
    def wrapper(*args, **kwargs):
        futures_not_loaded = 'scoop.futures' not in sys.modules
        controller_not_started = not (
            sys.modules['scoop.futures'].__dict__.get("_controller", None)
        )
        if futures_not_loaded or controller_not_started:
            raise NotStartedProperly("SCOOP was not started properly.\n"
                                     "Be sure to start your program with the "
                                     "'-m scoop' parameter. You can find "
                                     "further information in the "
                                     "documentation.")
        return func(*args, **kwargs)
    return wrapper