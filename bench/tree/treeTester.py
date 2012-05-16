from __future__ import print_function
import numpy.random
import time
import cPickle as pickle

Tree = None
mapfunc = None

def intCalc(times):
    x = 1
    for i in range(times):
        x += x * i

def floatCalc(times):
    x = 1.1
    for i in range(times):
        x += x * i

def generateTree(height,minChildren, maxChildren, a, scaleParametre):
    if height == 0:
        return (int(numpy.random.weibull(a)*scaleParametre),
                int(numpy.random.weibull(a)*scaleParametre), [])

    n = numpy.random.randint(minChildren, maxChildren)
    children = []
    for i in range(n):
        children.append(generateTree(height - 1,minChildren, maxChildren, a,
            scaleParametre))
    return (int(numpy.random.weibull(a)*scaleParametre),
            int(numpy.random.weibull(a)*scaleParametre), children)

def exportTree(tree, filename):
    f = open(filename, 'w')
    pickle.dump(tree, f)
    f.close()

def importTree(filename):
    f = open(filename, 'r')
    global Tree
    Tree = pickle.load(f)
    f.close()
    #return tree
    
def getTree(addresses):
    t = Tree
    for index in addresses:
        t = t[2][index]
    return t

def executeTree(address):
    """This function executes a tree. To limit the size of the arguments passed
    to the function, the tree must be loaded in memory in every worker. To do
    this, simply call "Tree = importTree(filename)" before using the startup 
    method of the parralisation library you are using"""
    localTree = getTree(address)
    intCalc(localTree[0])
    floatCalc(localTree[1])
    nextAddresses = [address + [i] for i in range(len(localTree[2]))]
    if len(localTree[2]) == 0:
        return False
    res = mapfunc(executeTree, nextAddresses)
    return True

def registerMap(newMap):
    global mapfunc
    mapfunc = newMap

if __name__=="__main__":
    tree = generateTree(3,10,30,100, 3000)
    exportTree(tree, "tree.txt")
#    t = importTree("bonjour.txt")
#    bt = time.time()
#    executeTree(t)
#    bench = time.time() - bt
#    print("fini:", bench)
