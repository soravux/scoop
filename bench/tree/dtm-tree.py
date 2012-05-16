import treeTester
from deap import dtm

filename = "tree.txt"

def main():
    #t = importTree(filename)
    return treeTester.executeTree([])

if __name__=="__main__":
    treeTester.importTree(filename)
    treeTester.registerMap(dtm.map)
    dtm.start(main)
