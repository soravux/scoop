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
import logging

try:
    import psutil
except ImportError:
    psutil = None


if sys.version_info < (3, 3):
    from imp import load_source as importFunction
    FileNotFoundError = IOError
else:
    import importlib.machinery
    importFunction = lambda name, path: importlib.machinery.SourceFileLoader(name, path).load_module()


import scoop
from ..broker.structs import BrokerInfo
from .. import discovery, utils
if sys.version_info < (2, 7):
    import scoop.backports.runpy as runpy
else:
    import runpy


class Bootstrap(object):
    """Set up SCOOP communication links and launches the client module"""
    def __init__(self):
        self.parser = None
        self.args = None
        self.verbose = 1

    def main(self):
        """Bootstrap an arbitrary script.
        If no agruments were passed, use discovery module to search and connect
        to a broker."""
        if self.args is None:
            self.parse()

        self.log = utils.initLogging(self.verbose)

        # Change to the desired directory
        if self.args.workingDirectory:
            os.chdir(self.args.workingDirectory)

        if not self.args.brokerHostname:
            self.log.info("Discovering SCOOP Brokers on network...")
            pools = discovery.Seek()
            if not pools:
                self.log.error("Could not find a SCOOP Broker broadcast.")
                sys.exit(-1)
            self.log.info("Found a broker named {name} on {host} port "
                          "{ports}".format(
                name=pools[0].name,
                host=pools[0].host,
                ports=pools[0].ports,
            ))
            self.args.brokerHostname = pools[0].host
            self.args.taskPort = pools[0].ports[0]
            self.args.metaPort = pools[0].ports[0]
            self.log.debug("Using following addresses:\n{brokerAddress}\n"
                           "{metaAddress}".format(
                                brokerAddress=self.args.brokerAddress,
                                metaAddress=self.args.metaAddress,
                            ))

            self.args.origin = True

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
        self.parser.add_argument('--brokerHostname',
                                 help="The routable hostname of a broker",
                                 default="")
        self.parser.add_argument('--externalBrokerHostname',
                                 help="Externally routable hostname of local "
                                      "worker",
                                 default="")
        self.parser.add_argument('--taskPort',
                                 help="The port of the broker task socket",
                                 type=int)
        self.parser.add_argument('--metaPort',
                                 help="The port of the broker meta socket",
                                 type=int)
        self.parser.add_argument('--size',
                                 help="The size of the worker pool",
                                 type=int,
                                 default=1)
        self.parser.add_argument('--nice',
                                 help="Adjust the niceness of the process",
                                 type=int,
                                 default=0)
        self.parser.add_argument('--debug',
                                 help="Activate the debug",
                                 action='store_true')
        self.parser.add_argument('--profile',
                                 help="Activate the profiler",
                                 action='store_true')
        self.parser.add_argument('--echoGroup',
                                 help="Echo the process Group ID before launch",
                                 action='store_true')
        self.parser.add_argument('--workingDirectory',
                                 help="Set the working directory for the "
                                      "execution",
                                 default=None)
        self.parser.add_argument('--backend',
                                 help="Choice of communication backend",
                                 choices=['ZMQ', 'TCP'],
                                 default='ZMQ')
        self.parser.add_argument('executable',
                                 nargs='?',
                                 help='The executable to start with scoop')
        self.parser.add_argument('args',
                                 nargs=argparse.REMAINDER,
                                 help='The arguments to pass to the executable',
                                 default=[])
        self.parser.add_argument('--verbose', '-v', action='count',
                                 help=("Verbosity level of this launch script"
                                      "(-vv for "
                                      "more)"), default=1)
        self.parser.add_argument('--quiet', '-q', action='store_true',
                                 help="Suppress the output")

    def parse(self):
        """Generate a argparse parser and parse the command-line arguments"""
        if self.parser is None:
            self.makeParser()
        self.args = self.parser.parse_args()
        self.verbose = self.args.verbose if not self.args.quiet else 0

    def setScoop(self):
        """Setup the SCOOP constants."""
        scoop.IS_RUNNING = True
        scoop.IS_ORIGIN = self.args.origin
        scoop.BROKER = BrokerInfo(
            self.args.brokerHostname,
            self.args.taskPort,
            self.args.metaPort,
            self.args.externalBrokerHostname
                if self.args.externalBrokerHostname
                else self.args.brokerHostname,
        )
        scoop.SIZE = self.args.size
        scoop.DEBUG = self.args.debug
        scoop.MAIN_MODULE = self.args.executable
        scoop.CONFIGURATION = {
          'headless': not bool(self.args.executable),
          'backend': self.args.backend,
        }
        scoop.logger = self.log
        if self.args.nice:
            if not psutil:
                scoop.logger.error("psutil not installed.")
                raise ImportError("psutil is needed for nice functionnality.")
            p = psutil.Process(os.getpid())
            p.set_nice(self.args.nice)

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
            sys.stderr.write('{0}\nFile: {1}\nIn path: {2}\n'.format(
                    str(e),
                    scoop.MAIN_MODULE,
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
        # Without this, the underneath import clashes with the top-level one
        global scoop

        if globs is None:
            globs = globals()

        # Show the current process Group ID if asked
        if self.args.echoGroup:
            sys.stdout.write(str(os.getpgrp()) + "\n")
            sys.stdout.flush()

            scoop.logger.info("Worker(s) launched using {0}".format(
                    os.environ['SHELL'],
                )
            )

        # import the user module
        if scoop.MAIN_MODULE:
            globs.update(self.setupEnvironment(self))

        # Start the user program
        from scoop import futures

        def futures_startup():
            """Execute the user code.
            Wraps futures._startup (SCOOP initialisation) over the user module.
            Needs """
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
                "./profile/{0}.prof".format(os.getpid())
            )
        else:
            try:
                futures_startup()
            finally:
                # Must reimport (potentially not there after bootstrap)
                import scoop

                # Ensure a communication queue exists (may happend when a
                # connection wasn't established such as cloud-mode wait).
                if scoop._control.execQueue:
                    scoop._control.execQueue.shutdown()

if __name__ == "__main__":
    b = Bootstrap()
    b.main()
