import treeTester
import multiprocessing
import sys

PROC = 1 if len(sys.argv) < 2 else int(sys.argv[1])

filename = "tree.txt"
pool = multiprocessing.Pool(processes=PROC)

def main():
    #t = importTree(filename)
    return treeTester.executeTree([])

if __name__=="__main__":
    treeTester.importTree(filename)
    treeTester.registerMap(pool.map)
    main()
