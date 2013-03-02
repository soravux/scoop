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
from .. import discovery
if sys.version_info < (2, 7):
    import scoop.backports.runpy as runpy
    from scoop.backports.dictconfig import dictConfig
else:
    import runpy
    from logging.config import dictConfig


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

        self.init_logging()

        if not self.args.brokerAddress:
            self.log.info("Discovering SCOOP Brokers on network...")
            pools = discovery.Seek()
            if not pools:
                self.log.error("Could not find a SCOOP Broker broadcast.\n")
                sys.exit(-1)
            self.log.info("Found a broker named {name} on {host} port "
                          "{ports}".format(
                name=pools[0].name,
                host=pools[0].host,
                ports=pools[0].ports,
            ))
            self.args.brokerAddress = "tcp://{host}:{port}".format(
                host=pools[0].host,
                port=pools[0].ports[0],
            )
            self.args.metaAddress = "tcp://{host}:{port}".format(
                host=pools[0].host,
                port=pools[0].ports[1],
            )
            self.log.debug("Using following addresses:\n{brokerAddress}\n"
                           "{metaAddress}".format(
                                brokerAddress=self.args.brokerAddress,
                                metaAddress=self.args.metaAddress,
                            ))
            # Make the workerName random
            import uuid
            self.args.workerName = str(uuid.uuid4())
            self.log.info("Using worker name {workerName}.".format(
                workerName=self.args.workerName,
            ))

            self.args.origin = True

        self.setScoop()

        self.run()

    def init_logging(self, log=None):
        verbose_levels = {
            -2: "CRITICAL",
            -1: "ERROR",
            0: "WARNING",
            1: "INFO",
            2: "DEBUG",
            3: "NOSET",
        }
        log_handlers = {
            "console":
            {

                "class": "logging.StreamHandler",
                "formatter": "SCOOPFormatter",
                "stream": "ext://sys.stdout",
            },
        }
        dict_log_config = {
            "version": 1,
            "handlers": log_handlers,
            "loggers":
            {
                "SCOOPLogger":
                {
                    "handlers": ["console"],
                    "level": verbose_levels[self.verbose],
                },
            },
            "formatters":
            {
                "SCOOPFormatter":
                {
                    "format":"[%(asctime)-15s] %(levelname)-7s %(message)s",
                },
            },
        }
        dictConfig(dict_log_config)
        self.log = logging.getLogger("SCOOPLogger")

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
        """Setup the SCOOP constants."""
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
