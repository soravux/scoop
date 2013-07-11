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
This example shows a way to parallelize binary tree traversal.
"""
import random
import sys
from scoop import futures


def maxTreeDepthDivide(rootValue, currentDepth=0, parallelLevel=2):
    """Finds a tree node that represents rootValue and computes the max depth
       of this tree branch.
       This function will emit new futures until currentDepth=parallelLevel"""
    thisRoot = exampleTree.search(rootValue)
    if currentDepth >= parallelLevel:
        return thisRoot.maxDepth(currentDepth)
    else:
        return max(
            futures.map(
                maxTreeDepthDivide,
                [
                    thisRoot.left.payload,
                    thisRoot.right.payload,
                ],
                currentDepth=currentDepth + 1,
                parallelLevel=parallelLevel,
            )
        )


class BinaryTreeNode(object):
    """A simple binary tree."""
    def __init__(self, payload=None, left=None, right=None):
        self.payload = payload
        self.left = left
        self.right = right

    def insert(self, value):
        """Insert a value in the tree"""
        if not self.payload or value == self.payload:
            self.payload = value
        else:
            if value <= self.payload:
                if self.left:
                    self.left.insert(value)
                else:
                    self.left = BinaryTreeNode(value)
            else:
                if self.right:
                    self.right.insert(value)
                else:
                    self.right = BinaryTreeNode(value)

    def maxDepth(self, currentDepth=0):
        """Compute the depth of the longest branch of the tree"""
        if not any((self.left, self.right)):
            return currentDepth
        result = 0
        for child in (self.left, self.right):
            if child:
                result = max(result, child.maxDepth(currentDepth + 1))
        return result

    def search(self, value):
        """Find an element in the tree"""
        if self.payload == value:
            return self
        else:
            if value <= self.payload:
                if self.left:
                    return self.left.search(value)
            else:
                if self.right:
                    return self.right.search(value)
        return None

if __name__ == '__main__':
    print("Beginning Tree generation.")

# Generate the same tree on every workers.
random.seed(314159265)
exampleTree = BinaryTreeNode(0)
for _ in range(128000):
    exampleTree.insert(random.randint(-sys.maxsize - 1, sys.maxsize))


if __name__ == '__main__':
    import time

    print("Tree generation done.")

    # Splits the tree in two and process the left and right branches parallely
    ts = time.time()
    presult = max(
        futures.map(
            maxTreeDepthDivide,
            [exampleTree.payload],
            parallelLevel=1,
        )
    )
    pts = time.time() - ts

    # Serial computation of tree depth
    ts = time.time()
    sresult = exampleTree.maxDepth()
    sts = time.time() - ts

    print(presult, sresult)
    
    print("Parallel time: {0:.5f}s\nSerial time:   {1:.5f}s".format(pts, sts))

    assert presult == sresult