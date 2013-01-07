from scoop import futures, shared
import scoop
import code

# Usage example:
# 
# >>> def myExample(inVal):
# ...     return inVal + 1
# ...
# >>> shared.shareConstant(myExample=myExample)
# >>> print(list(futures.map(myExample, range(1000))))
# >>> exit()

if __name__ == '__main__':
    code.interact(local=locals())