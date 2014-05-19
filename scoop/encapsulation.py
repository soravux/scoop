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
import os
from inspect import ismodule
from functools import partial
try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import copyreg
    from io import BytesIO as FileLikeIO
    from io import BufferedReader as FileType
except ImportError:
    # Support for Python 2.X
    import copy_reg as copyreg
    from StringIO import StringIO as FileLikeIO
    from types import FileType as FileType

import scoop


def functionFactory(in_code, name, defaults, globals_, imports):
    """Creates a function at runtime using binary compiled inCode"""
    def generatedFunction():
        pass
    generatedFunction.__code__ = marshal.loads(in_code)
    generatedFunction.__name__ = name
    generatedFunction.__defaults = defaults
    generatedFunction.__globals__.update(pickle.loads(globals_))
    for key, value in imports.items():
        imported_module = __import__(value)
        scoop.logger.debug("Dynamically loaded module {0}".format(value))
        generatedFunction.__globals__.update({key: imported_module})
    return generatedFunction


class FunctionEncapsulation(object):
    """Encapsulates a function in a serializable way.

    This is used by the sharing module (setConst).
    Used for lambda functions and function defined on-the-fly (interactive
    shell)"""
    def __init__(self, in_func, name):
        """Creates a serializable (picklable) object of a function"""
        self.code = marshal.dumps(in_func.__code__)
        self.name = name
        self.defaults = in_func.__defaults__
        # Pickle references to functions used in the function
        used_globals = {} # name: function
        used_modules = {} # used name: origin module name
        for key, value in in_func.__globals__.items():
            if key in in_func.__code__.co_names:
                if ismodule(value):
                    used_modules[key] = value.__name__
                else:
                    used_globals[key] = value
        self.globals = pickle.dumps(used_globals, pickle.HIGHEST_PROTOCOL)
        self.imports = used_modules

    def __call__(self, *args, **kwargs):
        """Called by local worker (which doesn't _communicate this class)"""
        return self.getFunction()(*args, **kwargs)

    def __name__(self):
        return self.name

    def getFunction(self):
        """Called by remote workers. Useful to populate main module globals()
        for interactive shells. Retrieves the serialized function."""
        return functionFactory(
            self.code,
            self.name,
            self.defaults,
            self.globals,
            self.imports,
        )


class ExternalEncapsulation(object):
    """Encapsulates an arbitrary file in a serializable way"""
    def __init__(self, in_filepath):
        """Creates a serializable (picklable) object of inFilePath"""
        self.filename = os.path.basename(in_filepath)
        with open(in_filepath, "rb") as fhdl:
            self.data = pickle.dumps(fhdl, pickle.HIGHEST_PROTOCOL)

    def writeFile(self, directory=None):
        """Writes back the file to a temporary path (optionaly specified)"""
        if directory:
            # If a directory was specified
            full_path = os.path.join(directory, self.filename)
            with open(full_path, 'wb') as f:
                f.write(pickle.loads(self.data).read())
            return full_path

        # if no directory was specified, create a temporary file
        this_file = tempfile.NamedTemporaryFile(delete=False)
        this_file.write(pickle.loads(self.data).read())
        this_file.close()

        return this_file.name


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


def makeLambdaPicklable(lambda_function):
    """Take input lambda function l and makes it picklable."""
    if isinstance(lambda_function,
                  type(lambda: None)) and lambda_function.__name__ == '<lambda>':
        def __reduce_ex__(proto):
            # TODO: argdefs, closure
            return unpickleLambda, (marshal.dumps(lambda_function.__code__), )
        lambda_function.__reduce_ex__ = __reduce_ex__
    return lambda_function


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
    return unpickleFileLike, (position, data)

copyreg.pickle(FileType, pickleFileLike, unpickleFileLike)
