# -*- coding: utf-8 -*-
from treeTester import *
from deap import dtm

filename = "tree.txt"

def main():
    return executeTree([])

if __name__=="__main__":
    importTree(filename)
    registerMap(dtm.map)
    print(dtm.start(main))
    
    


