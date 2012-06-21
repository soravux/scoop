# -*- coding: utf-8 -*-
from Tree import *
import sys
import time
from scoop import futures, FEDERATION_SIZE

def main():
    return executeTree()

importTree(sys.argv[1] if len(sys.argv) > 1 else "tree.txt")
registerMap(futures.map)

if __name__=="__main__":
    bt = time.time()
    main()
    totalTime = time.time() - bt
    print("total time : {}\ncores : {}".format(totalTime, FEDERATION_SIZE))