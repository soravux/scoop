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

import scoop


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
# List of group ids for which we advertized we are working on
notified = []
comm_dst = {}
comm_src = defaultdict(list)


def get_future_group_ids(inFuture):
    """Produces the group ids of a given future."""
    uniqueReferences = []
    try:
        for cb in inFuture.callback:
            if cb.groupID:
                uniqueReferences.append(cb.groupID)
    except IndexError:
        raise Exception("Could not find reduction reference.")
    return uniqueReferences


def reduction(inFuture, operation):
    """Generic reduction method. Subclass it (using partial() is recommended)
    to specify an operation or enhance its features if needed."""
    global total

    uniqueReferences = get_future_group_ids(inFuture)
    for uniqueReference in uniqueReferences:
        # This section can not be a defaultdict because the reduction answer
        # could be any data structure.
        if uniqueReference not in total:
            total[uniqueReference] = inFuture.result()
        else:
            total[uniqueReference] = operation(total[uniqueReference],
                                               inFuture.result())
    inFuture.resultValue = total[uniqueReferences[0]]


class ReductionTree(object):
    """Despite this class name, it's simply a tree node"""
    def __init__(self, inList, parent=None):
        """Generate a tree"""
        try:
            self.payload = inList.pop(0)
        except IndexError:
            self.payload = None
        self.parent = parent
        self.children = []
        # Make half the elements to the left, the rest to the right
        left_elements = inList[: int((len(inList) - 1) / 2)]
        if left_elements:
            self.children.append(ReductionTree(left_elements, parent=self))
        right_elements = inList[int((len(inList) - 1) / 2) :]
        if right_elements:
            self.children.append(ReductionTree(right_elements, parent=self))

    def dfs(self, value):
        if self.payload == value:
            return self

        for child in self.children:
            search = child.dfs(value)
            if search:
                return search

    def get_my_parent(self):
        try:
            return self.dfs(scoop.worker).parent.payload
        except AttributeError:
            return None

    def get_my_children(self):
        return [x.payload for x in self.dfs(scoop.worker).children if x.payload]


def cleanGroupID(inGroupID):
    global total
    total.pop(inGroupID)
    sequence.pop(inGroupID)
    comm_dst.pop(inGroupID)
    comm_src.pop(inGroupID)
