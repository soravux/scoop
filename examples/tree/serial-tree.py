# -*- coding: utf-8 -*-
from Tree import *
import sys
import time


def main():
    executeTree()

importTree(sys.argv[1] if len(sys.argv) > 1 else "tree.txt")
registerMap(map)
    
if __name__=="__main__":
    bt = time.time()
    main()
    totalTime = time.time() - bt
    print("Serial total time : {}".format(totalTime))