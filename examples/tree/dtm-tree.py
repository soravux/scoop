# -*- coding: utf-8 -*-
from treeTester import *
import sys
from deap import dtm

registerMap(dtm.map)

def main():
    return executeTree()

if __name__=="__main__":
    importTree(sys.argv[1] if len(sys.argv) > 1 else "tree.txt")
    #registerMap(dtm.map)
    print(dtm.start(main))
