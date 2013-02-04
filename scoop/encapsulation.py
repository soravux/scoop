#
#    This file is part of Scalable COncurrent Operations in Python (SCOOP).
#
#    SCOOP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    SCOOP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with SCOOP. If not, see <http://www.gnu.org/licenses/>.
#
import marshal
import tempfile
import types
import pickle
from functools import partial

try:
    import copyreg
    from io import BytesIO as FileLikeIO
    from io import IOBase as FileType
except ImportError:
    # copyreg is named copy_reg under Python 2.X
    import copy_reg as copyreg
    from StringIO import StringIO as FileLikeIO
    from types import FileType as FileType


def functionFactory(inCode):
    """Creates a function at runtime using binary compiled inCode"""
    def generatedFunction():
        pass
    generatedFunction.__code__ = marshal.loads(inCode)
    return generatedFunction


# TODO: Replace this by copyreg on FunctionType
class FunctionEncapsulation(object):
    """Encapsulates a function in a serializable way"""
    def __init__(self, inFunc):
        """Creates a serializable (picklable) object of a function"""
        self.code = marshal.dumps(inFunc.__code__)
        # TODO: __defaults__, docstrings

    def getFunction(self):
        """Retrieve the serialized function"""
        return functionFactory(self.code)


# TODO: Replace this by copyreg using FileLike
class ExternalEncapsulation(object):
    """Encapsulates an arbitrary file in a serializable way"""
    def __init__(self, inFilePath):
        """Creates a serializable (picklable) object of inFilePath"""
        with open(inFilePath, "rb") as fhdl:
            self.data = fhdl.read()

    def writeFile(self):
        """Writes back the file to a temporary path"""
        thisFile = tempfile.NamedTemporaryFile(delete=False)
        thisFile.write(self.data)
        thisFile.close()

        return thisFile.name


# The following block handles callables pickling and unpickling

# TODO: Make a factory to generate unpickling functions
def unpickleLambda(pickled_callable):
    # TODO: Set globals to user module
    return types.LambdaType(marshal.loads(pickled_callable), globals())

def unpickleMethodType(pickled_callable):
    # TODO: Set globals to user module
    return types.MethodType(marshal.loads(pickled_callable), globals())


def pickleCallable(callable_, unpickle_func):
    # TODO: Pickle also argdefs and closure
    return unpickle_func, (marshal.dumps(callable_.__code__), )

pickle_lambda = partial(pickleCallable, unpickle_func=unpickleLambda)
pickle_method = partial(pickleCallable, unpickle_func=unpickleMethodType)
copyreg.pickle(types.LambdaType, pickle_lambda, unpickleLambda)
copyreg.pickle(types.MethodType, pickle_method, unpickleMethodType)


# The following block handles file-like objects pickling and unpickling

def unpickleFileLike(position, data):
    file_ = FileLikeIO(data)
    file_.seek(position)
    return file_

def pickleFileLike(file_):
    position = file_.tell()
    file_.seek(0)
    data = file_.read()
    file_.seek(position)
    return file_unpickler, (position, data)

copyreg.pickle(FileType, pickleFileLike, unpickleFileLike)
