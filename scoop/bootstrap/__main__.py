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

from __future__ import print_function
import sys
if sys.version_info < (2, 7):
    import scoop.backports.runpy as runpy
else:
    import runpy
import os
import functools
import argparse
import scoop


def makeParser():
    parser = argparse.ArgumentParser(description='Starts the executable.',
                                     prog=("{0} -m scoop.bootstrap"
                                           ).format(sys.executable))

    parser.add_argument('--origin',
                        help="To specify that the worker is the origin",
                        action='store_true')
    parser.add_argument('--workerName', help="The name of the worker",
                        default="worker0")
    parser.add_argument('--brokerName', help="The name of the broker",
                        default="broker")
    parser.add_argument('--brokerAddress',
                        help="The tcp address of the broker written "
                             "tcp://address:port",
                        default="")
    parser.add_argument('--metaAddress',
                        help="The tcp address of the info written "
                             "tcp://address:port",
                        default="")
    parser.add_argument('--size',
                        help="The size of the worker pool",
                        type=int,
                        default=1)
    parser.add_argument('--debug',
                        help="Activate the debug",
                        action='store_true')
    parser.add_argument('--profile',
                        help="Activate the profiler",
                        action='store_true')
    parser.add_argument('executable',
                        nargs=1,
                        help='The executable to start with scoop')
    parser.add_argument('args',
                        nargs=argparse.REMAINDER,
                        help='The arguments to pass to the executable',
                        default=[])
    return parser


def main():
    # Generate a argparse parser and parse the command-line arguments
    parser = makeParser()
    args = parser.parse_args()

    # Setup the SCOOP constants
    scoop.IS_ORIGIN = args.origin
    scoop.WORKER_NAME = args.workerName.encode()
    scoop.BROKER_NAME = args.brokerName.encode()
    scoop.BROKER_ADDRESS = args.brokerAddress.encode()
    scoop.META_ADDRESS = args.metaAddress.encode()
    scoop.SIZE = args.size
    scoop.DEBUG = args.debug
    scoop.worker = (scoop.WORKER_NAME, scoop.BROKER_NAME)

    profile = True if args.profile else False

    # get the module path in the Python path
    sys.path.append(os.path.join(os.getcwd(),
                    os.path.dirname(args.executable[0])))

    # temp values to keep the args
    executable = args.executable[0]

    # Add the user arguments to argv
    sys.argv = sys.argv[:1]
    sys.argv += args.args

    # import the user module into the global dictionary
    # equivalent to from {user_module} import *
    user_module = __import__(os.path.basename(executable)[:-3])
    try:
        attrlist = user_module.__all__
    except AttributeError:
        attrlist = dir(user_module)
    for attr in attrlist:
        globals()[attr] = getattr(user_module, attr)

    if not profile:
        # Start the user program
        from scoop import futures
        futures._startup(functools.partial(runpy.run_path,
                                           executable,
                                           init_globals=globals(),
                                           run_name="__main__"))
    else:
        from scoop import futures
        import cProfile
        cProfile.run("""futures._startup(functools.partial(runpy.run_path,
                        "{0}",
                        init_globals=globals(),
                        run_name="__main__"))""".format(executable),
                     scoop.WORKER_NAME)

if __name__ == "__main__":
    main()
