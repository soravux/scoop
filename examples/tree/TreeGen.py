import argparse
import Tree

if __name__=="__main__":

    parser = argparse.ArgumentParser(description="Creates a random tree "
                                                 "structure")
    parser.add_argument('--height',
                          help='The height of the tree.',
                          type=int,
                          default=5)
    parser.add_argument('--minChildren', '-m',
                           help="The minimum number of children by nodes",
                           type=int,
                           default=0)
    parser.add_argument('--maxChildren', '-M',
                           help="The maximum number of children by nodes",
                           type=int,
                           default=8)
    parser.add_argument('--alpha', '-a',
                           help="The 'a' parameter of the Weibull distribution "
                           "used to create the task length.",
                           type=float,
                           default=1)
    parser.add_argument('--scale', '-s',
                           help="The mean time of each task.",
                           type = float,
                           default=1)
    parser.add_argument('--filename', '-f',
                           help="The filename to save the tree.",
                           default="tree.txt")

    args = parser.parse_args()
    
    if args.minChildren > args.maxChildren:
        args.maxChildren = args.minChildren + 1
    
    tree = Tree.Tree(args.height,
                args.minChildren,
                args.maxChildren,
                args.alpha,
                *Tree.calibrate(args.scale))
    Tree.exportTree(tree, args.filename)
    print("Generated :\n{0}".format(tree))
