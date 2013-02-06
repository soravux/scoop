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
import sys
import os
import functools
import argparse
if sys.version_info < (3, 3):
    from imp import load_source as importFunction
else:
    import importlib.machinery
    importFunction = lambda name, path: importlib.machinery.SourceFileLoader(name, path).load_module()


import scoop
if sys.version_info < (2, 7):
    import scoop.backports.runpy as runpy
else:
    import runpy


class Bootstrap(object):
    """Set up SCOOP communication links and launches the client module"""
    def __init__(self):
        self.parser = None
        self.args = None

    def main(self):
        if self.args is None:
            self.parse()

        self.setScoop()

        self.run()

    def makeParser(self):
        """Generate the argparse parser object containing the bootloader
           accepted parameters
        """
        self.parser = argparse.ArgumentParser(description='Starts the executable.',
                                              prog=("{0} -m scoop.bootstrap"
                                                    ).format(sys.executable))

        self.parser.add_argument('--origin',
                                 help="To specify that the worker is the origin",
                                 action='store_true')
        self.parser.add_argument('--workerName', help="The name of the worker",
                                 default="0")
        self.parser.add_argument('--brokerName', help="The name of the broker",
                                 default="broker")
        self.parser.add_argument('--brokerAddress',
                                 help="The tcp address of the broker written "
                                    "tcp://address:port",
                                 default="")
        self.parser.add_argument('--metaAddress',
                                 help="The tcp address of the info written "
                                    "tcp://address:port",
                                 default="")
        self.parser.add_argument('--size',
                                 help="The size of the worker pool",
                                 type=int,
                                default=1)
        self.parser.add_argument('--debug',
                                 help="Activate the debug",
                                 action='store_true')
        self.parser.add_argument('--profile',
                                 help="Activate the profiler",
                                 action='store_true')
        self.parser.add_argument('--echoGroup',
                                 help="Echo the process Group ID before launch",
                                 action='store_true')
        self.parser.add_argument('executable',
                                 nargs='?',
                                 help='The executable to start with scoop')
        self.parser.add_argument('args',
                                 nargs=argparse.REMAINDER,
                                 help='The arguments to pass to the executable',
                                 default=[])

    def parse(self):
        """Generate a argparse parser and parse the command-line arguments"""
        if self.parser is None:
            self.makeParser()
        self.args = self.parser.parse_args()

    def setScoop(self):
        """Setup the SCOOP constants"""
        scoop.is_running = True
        scoop.IS_ORIGIN = self.args.origin
        scoop.WORKER_NAME = self.args.workerName.encode()
        scoop.BROKER_NAME = self.args.brokerName.encode()
        scoop.BROKER_ADDRESS = self.args.brokerAddress.encode()
        scoop.META_ADDRESS = self.args.metaAddress.encode()
        scoop.SIZE = self.args.size
        scoop.DEBUG = self.args.debug
        scoop.worker = (scoop.WORKER_NAME, scoop.BROKER_NAME)
        scoop.MAIN_MODULE = self.args.executable
        scoop.CONFIGURATION = {
          'headless': not bool(self.args.executable),
        }

        if scoop.DEBUG or self.args.profile:
            from scoop import _debug

    @staticmethod
    def setupEnvironment(self=None):
        """Set the environment (argv, sys.path and module import) of
        scoop.MAIN_MODULE.
        """
        # get the module path in the Python path
        sys.path.append(os.path.dirname(os.path.abspath(scoop.MAIN_MODULE)))

        # Add the user arguments to argv
        sys.argv = sys.argv[:1]
        if self:
            sys.argv += self.args.args

        try:
            user_module = importFunction(
                "SCOOP_WORKER",
                scoop.MAIN_MODULE,
            )
        except FileNotFoundError as e:
            # Could not find file
            sys.stderr.write('{0}\nIn path: {1}\n'.format(
                str(e),
                sys.path[-1],
                )
            )
            sys.stderr.flush()
            sys.exit(-1)

        globs = {}
        try:
            attrlist = user_module.__all__
        except AttributeError:
            attrlist = dir(user_module)
        for attr in attrlist:
            globs[attr] = getattr(user_module, attr)

        if self:
            return globs
        return user_module

    def run(self, globs=None):
        """Import user module and start __main__
           passing globals() is required when subclassing in another module
        """
        if globs is None:
            globs = globals()

        # Show the current process Group ID if asked
        if self.args.echoGroup:
            sys.stdout.write(str(os.getpgrp()) + "\n")
            sys.stdout.flush()

        # import the user module
        if scoop.MAIN_MODULE:
            globs.update(self.setupEnvironment(self))

        # Start the user program
        from scoop import futures

        def futures_startup():
            return futures._startup(
                functools.partial(
                    runpy.run_path,
                    scoop.MAIN_MODULE,
                    init_globals=globs,
                    run_name="__main__"
                )
            )

        if self.args.profile:
            import cProfile
            # runctx instead of run is required for local function
            try:
                os.makedirs("profile")
            except:
                pass
            cProfile.runctx(
                "futures_startup()",
                globs,
                locals(),
                "./profile/{0}.prof".format("-".join(scoop.DEBUG_IDENTIFIER))
            )
        else:
            futures_startup()


if __name__ == "__main__":
    b = Bootstrap()
    b.main()
