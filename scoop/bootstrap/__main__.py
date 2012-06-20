#!/usr/bin/env python
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


from scoop.futures import _startup
import runpy
import sys
import os
import functools
import argparse

parser = argparse.ArgumentParser(description='Starts the executable.',
                                 prog="{0} -m scoop.bootstrap".format(sys.executable))
parser.add_argument('executable',
                    nargs=1,
                    help='The executable to start with scoop')
parser.add_argument('args',
                    nargs=argparse.REMAINDER,
                    help='The arguments to pass to the executable',
                    default=[])
args = parser.parse_args()


if __name__ == "__main__":
    # get the module path in the Python path
    sys.path.append(os.path.join(os.getcwd(), os.path.dirname(args.executable[0])))
    
    # import the user module into the global dictionary
    # equivalent to from {user_module} import *
    user_module = __import__(os.path.basename(args.executable[0])[:-3])
    try:
        attrlist = user_module.__all__
    except AttributeError:
        attrlist = dir(user_module)
    for attr in attrlist:
        globals()[attr] = getattr(user_module, attr)

    # Add the user arguments to argv
    sys.argv += args.args
    # Setup the scoop constants

    # TODO add the scoop constants

    # Startup the program
    _startup(functools.partial(runpy.run_path, args.executable[0],
             init_globals=globals(),run_name="__main__"))
