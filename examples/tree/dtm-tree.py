# -*- coding: utf-8 -*-
from Tree import *
import sys
import time
from deap import dtm

def main():
    return executeTree()
    
importTree(sys.argv[1] if len(sys.argv) > 1 else "tree.txt")
registerMap(dtm.map)

if __name__=="__main__":
    bt = time.time()
    dtm.start(main)
    totalTime = time.time() - bt
    print("total time : {}".format(totalTime))