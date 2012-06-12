from __future__ import print_function
import math
import numpy.random
import time
import argparse
try:
    import cPickle as pickle
except ImportError:
    import pickle

graph = True
try:
    import pydot
except ImportError:
    graph = False

GlobalTree = None
mapfunc = None
nodeDone = 0
maxHeight = 0
maxDepth = 0
if graph:
    g = pydot.Dot()
    h = 0

class Tree():
    def __init__(self, height, minChildren, maxChildren, a, intMean, floatMean):
        global maxHeight, maxDepth, g, h
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
        if graph:
            self.node = pydot.Node( h )
            g.add_node( self.node )
            h += 1
        
        if height == 0:
            self.leaves = 1
            return

        # Generate children
        n = numpy.random.randint(minChildren, maxChildren)
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
            if graph:
                g.add_edge( pydot.Edge( self.node, child.node ) )
            
        self.height = maxHeight - maxDepth

    def __str__(self):
        if graph:
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
    method of the parralisation library you are using"""
    global nodeDone
    # Get tree subsection
    localTree = getTree(address)
    # Execute tasks
    localTree.intCalc()
    localTree.floatCalc()
    nodeDone += 1
    print("{}/{}".format(nodeDone, GlobalTree.nodes))
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
    x = numpy.random.randint(1, 9)
    bt = time.time()
    for i in range(1000000):
        x = (x + x * i) % 2**32
    total = time.time() - bt
    intValue = meanTime * 1000000 / total / 2
    
    x = 1.1 * numpy.random.randint(1, 9)
    bt = time.time()
    for i in range(1000000):
        x = (x + x * i) % 2**32
    total = time.time() - bt
    floatValue = meanTime * 1000000 / total / 2
    
    print(intValue, floatValue)
    return intValue, floatValue

if __name__=="__main__":

    parser = argparse.ArgumentParser(description="Creates a random tree "
                                                 "structure")
    parser.add_argument('--height',
                          help='The height of the tree.',
                          type=int,
                          default=5)
    parser.add_argument('--minChildren', '-m',
                           help="The minimum number of children by nodes",
                           type=int,
                           default=0)
    parser.add_argument('--maxChildren', '-M',
                           help="The maximum number of children by nodes",
                           type=int,
                           default=8)
    parser.add_argument('--alpha', '-a',
                           help="The 'a' parameter of the Weibull distribution "
                           "used to create the task length.",
                           type=float,
                           default=1)
    parser.add_argument('--scale', '-s',
                           help="The mean time of each task.",
                           type = float,
                           default=1)
    parser.add_argument('--filename', '-f',
                           help="The filename to save the tree.",
                           default="tree.txt")

    args = parser.parse_args()
    
    if args.minChildren > args.maxChildren:
        args.maxChildren = args.minChildren + 1
    
    tree = Tree(args.height,
                args.minChildren,
                args.maxChildren,
                args.alpha,
                *calibrate(args.scale))
    exportTree(tree, args.filename)
    print("Generated :\n{0}".format(tree))
