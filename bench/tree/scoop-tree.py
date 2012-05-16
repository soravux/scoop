import treeTester
from scoop import futures

filename = "tree.txt"

def main():
    #t = importTree(filename)
    return treeTester.executeTree([])

if __name__=="__main__":
    treeTester.importTree(filename)
    treeTester.registerMap(futures.mapJoin)
    futures.startup(main)
