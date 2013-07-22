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
from collections import defaultdict


class Counter(object):
    def __init__(self, *args):
        self.iterator = itertools.count(*args)
        self.current_value = next(self.iterator)

    def next(self):
        """Support for Python 2."""
        self.__next__()

    def __next__(self):
        ret_val = self.current_value
        self.current_value = next(self.iterator)
        return ret_val

    def __int__(self):
        return self.current_value


# Contains the reduction of every child ran on this worker
total = {}
# Contains the number of tasks reduced for this worker
# Set the number of ran futures for a given group
sequence = defaultdict(Counter)
# Reception buffer upon task termination: group_id { worker id : (qty, result)}
answers = defaultdict(dict)


def reduction(inFuture, operation):
    """Generic reduction method. Subclass it (using partial() is recommended)
    to specify an operation or enhance its features if needed."""
    global total

    uniqueReferences = []
    try:
        for cb in inFuture.callback:
            if cb.groupID:
                uniqueReferences.append(cb.groupID)
    except IndexError:
        raise Exception("Could not find reduction reference.")
    for uniqueReference in uniqueReferences:
        if uniqueReference not in total:
            total[uniqueReference] = inFuture.result()
        else:
            total[uniqueReference] = operation(total[uniqueReference],
                                               inFuture.result())
    inFuture.resultValue = total[uniqueReferences[0]]


def cleanGroupID(inGroupID):
    global total
    try:
        del total[inGroupID]
    except KeyError:
        pass