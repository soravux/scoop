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
        print("intcalc: ", self.intRange)
        x = 1
        for i in range(self.intRange):
            x = (x + x * i) % 2**32
        print("intcalc fin")

    def floatCalc(self):
        print("floatcalc", self.floatRange)
        x = 1.1
        for i in range(self.floatRange):
            x = (x + x * i) % 2**32
        print("floatcalc fin")

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
    # Get tree subsection
    localTree = getTree(address)
    # Execute tasks
    localTree.intCalc()
    localTree.floatCalc()
    # Select next nodes to be 
    nextAddresses = [address + [i] for i in range(len(localTree.children))]
    print(nextAddresses)
    if len(localTree.children) == 0:
        return 1
    res = sum(mapfunc(executeTree, nextAddresses))
    assert res == localTree.leaves, "Test failed: res = {0}, leaves = {1}".format(res, localTree.leaves)
    if localTree.height == (GlobalTree.height - 1):
        print("{}/{}".format(res, GlobalTree.leaves))
    return res

def exportTree(tree, filename):
    f = open(filename, 'wb')
    pickle.dump(tree, f)
    f.close()

def importTree(filename):
    f = open(filename, 'rb')
    global GlobalTree
    GlobalTree = pickle.load(f)
    f.close()
    #return tree

def registerMap(newMap):
    global mapfunc
    mapfunc = newMap

def execfloat(floatValue):
    x = 1.1 * numpy.random.randint(1, 9)
    for i in range(int(math.floor(floatValue))):
        x = (x + x * i) % 2**32
    
def calibrate(meanTime):
    acceptedMin = meanTime - (meanTime * 0.05)
    acceptedMax = meanTime + (meanTime * 0.05)
    total = 0
    intValue = 1
    while total < acceptedMin or total > acceptedMax:
        try:
            intValue =  meanTime * intValue / total
        except ZeroDivisionError:
            intValue = 1
        bt = time.time()
        x = 0
        for i in range(int(math.floor(intValue))):
            x = (x + x * i) % 2**32
        total = time.time() - bt
    
    print(total)
    total = 0
    floatValue = 1
    
    while total < acceptedMin or total > acceptedMax:
        try:
            floatValue =  meanTime * floatValue / total
        except ZeroDivisionError:
            floatValue = 1
        bt = time.time()
        execfloat(int(math.floor(floatValue)))
        #x = 1.1 * numpy.random.randint(1, 9)
        #for i in range():
        #    x = (x + x * i) % 2**32
        total = time.time() - bt
    print(intValue, floatValue)
    print(total)
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
    
    tree = Tree(args.height, args.minChildren, args.maxChildren,
                args.alpha, *calibrate(args.scale))
    exportTree(tree, args.filename)
    print("Generated :\n{0}".format(tree))
