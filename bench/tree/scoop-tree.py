# -*- coding: utf-8 -*-
from treeTester import *
from scoop import futures

filename = "tree.txt"

def main():
    return executeTree([])

if __name__=="__main__":
    importTree(filename)
    registerMap(futures.mapJoin)
    print(futures.startup(main))
