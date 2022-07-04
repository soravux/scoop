from __future__ import print_function
import random
import math
import time
import argparse
try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import pydot
except ImportError:
    pydot = None

GlobalTree = None
mapfunc = None
maxHeight = 0
maxDepth = 0
if pydot:
    g = pydot.Dot()
    h = 0

class Tree():
    def __init__(self, height, minChildren, maxChildren, a, intMean, floatMean):
        global maxHeight, maxDepth, g, h
        import numpy.random
        self.intRange = int(numpy.random.weibull(a)*intMean)
        self.floatRange = int(numpy.random.weibull(a)*floatMean)

        # Record effective height of tree
        if maxHeight == 0:
            maxHeight = height
            maxDepth = height
        elif maxDepth > height:
            maxDepth = height
        self.children = [] 
        self.nodes = 1
        self.leaves = 0
        
        # Generate a new node in graph
        if pydot:
            self.node = pydot.Node( h )
            g.add_node( self.node )
            h += 1
        
        if height == 0:
            self.leaves = 1
            return

        # Generate children
        n = random.randint(minChildren, maxChildren)
        self.children = []
        for i in range(n):
            self.children.append(Tree(height - 1,
                                      minChildren,
                                      maxChildren,
                                      a,
                                      intMean,
                                      floatMean))

        # Keep statistics
        if len(self.children) == 0:
            self.leaves = 1
        
        for child in self.children:
            self.nodes += child.nodes
            self.leaves += child.leaves
            if pydot:
                g.add_edge( pydot.Edge( self.node, child.node ) )
                del child.node
            
        self.height = maxHeight - maxDepth
        if pydot and height == maxHeight:
            del self.node

    def __str__(self):
        if pydot:
            g.write_png("graph.png")
        return ("height : {0}\n"
                "leaves : {1}\n"
                "nodes  : {2}").format(self.height,
                                       self.leaves,
                                       self.nodes)

    def intCalc(self):
        x = 1
        for i in range(self.intRange):
            x = (x + x * i) % 2**32

    def floatCalc(self):
        x = 1.1
        for i in range(self.floatRange):
            x = (x + x * i) % 2**32

def getTree(addresses):
    t = GlobalTree
    for index in addresses:
        t = t.children[index]
    return t

def executeTree(address=[]):
    """This function executes a tree. To limit the size of the arguments passed
    to the function, the tree must be loaded in memory in every worker. To do
    this, simply call "Tree = importTree(filename)" before using the startup
    method of the parallelisation library you are using"""
    global nodeDone
    # Get tree subsection
    localTree = getTree(address)
    # Execute tasks
    localTree.intCalc()
    localTree.floatCalc()
    # Select next nodes to be executed
    nextAddresses = [address + [i] for i in range(len(localTree.children))]
    if len(localTree.children) == 0:
        return 1
    # Execute the children
    res = sum(mapfunc(executeTree, nextAddresses))
    assert res == localTree.leaves, (
        "Test failed: res = {0}, leaves = {1}").format(res, localTree.leaves)
    return res

def exportTree(tree, filename):
    f = open(filename, 'wb')
    pickle.dump(tree, f)
    f.close()

def importTree(filename):
    global GlobalTree
    f = open(filename, 'rb')
    GlobalTree = pickle.load(f)
    f.close()

def registerMap(newMap):
    global mapfunc
    mapfunc = newMap    
    
def calibrate(meanTime):
    x = random.randint(1, 9)
    bt = time.time()
    for i in range(1000000):
        x = (x + x * i) % 2**32
    total = time.time() - bt
    intValue = meanTime * 1000000 / total / 2
    
    x = 1.1 * random.randint(1, 9)
    bt = time.time()
    for i in range(1000000):
        x = (x + x * i) % 2**32
    total = time.time() - bt
    floatValue = meanTime * 1000000 / total / 2
    
    print(intValue, floatValue)
    return intValue, floatValue