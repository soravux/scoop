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

# Contains the reduction of every child ran on this worker
total = {}
# Set the number of ran futures for a given group
sequence = defaultdict(itertools.count)

def reduction(inFuture, operation):
    """Generic reduction method. Subclass it (using partial() is recommended)
    to specify an operation or enhance its features if needed."""
    global total
    try:
        uniqueReference = [cb.groupID for cb in inFuture.callback]
    except IndexError:
        raise Exception("Could not find reduction reference.")
    total[uniqueReference[0]] = operation(inFuture.result(),
                                          total.get(uniqueReference[0], 0))
    inFuture.resultValue = total[uniqueReference[0]]

def cleanGroupID(inGroupID):
    global total
    try:
        del total[inGroupID]
    except KeyError:
        pass