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
# Global imports
import argparse
import os
import sys
import socket
import subprocess
import time
import logging
import traceback
import signal
from threading import Thread

# Local imports
from scoop import utils
from scoop.launch import Host
from scoop.launch.brokerLaunch import localBroker, remoteBroker
from .broker.structs import BrokerInfo
import scoop

try:
    signal.signal(signal.SIGQUIT, utils.KeyboardInterruptHandler)
except AttributeError:
    # SIGQUIT doesn't exist on Windows
    signal.signal(signal.SIGTERM, utils.KeyboardInterruptHandler)


class ScoopApp(object):
    """SCOOP application. Coordinates the broker and worker launches."""
    LAUNCH_HOST_CLASS = Host

    def __init__(self, hosts, n, b, verbose, python_executable,
            externalHostname, executable, arguments, tunnel, path, debug,
            nice, env, profile, pythonPath, prolog, backend):
        # Assure setup sanity
        assert type(hosts) == list and hosts, ("You should at least "
                                               "specify one host.")
        self.workersLeft = n
        self.createdSubprocesses = []

        # launch information
        self.python_executable = python_executable[0]
        self.pythonpath = pythonPath
        self.prolog = prolog
        self.n = n
        self.b = b
        self.tunnel = tunnel
        self.executable = executable
        self.args = arguments
        self.verbose = verbose
        self.path = path
        self.debug = debug
        self.nice = nice
        self.profile = profile
        self.backend = backend
        self.errors = None

        # Logging configuration
        if self.verbose > 2:
            self.verbose = 2

        scoop.logger = utils.initLogging(
            verbosity=self.verbose,
            name="launcher",
        )

        # Show runtime information (useful for debugging)
        scoop.logger.info("SCOOP {0} {1} on {2} using Python {3}, API: {4}".format(
                scoop.__version__,
                scoop.__revision__,
                sys.platform,
                sys.version.replace("\n", ""),
                sys.api_version,
            )
        )

        if env in ["SLURM","PBS", "SGE"]:
            scoop.logger.info("Detected {0} environment.".format(env))
        scoop.logger.info("Deploying {0} worker(s) over {1} "
                      "host(s).".format(
                          n,
                          len(hosts)
                      )
        )

        # Handling External Hostname
        self.externalHostname = '127.0.0.1' if self.tunnel else externalHostname
        scoop.logger.debug('Using hostname/ip: "{0}" as external broker '
                      'reference.'.format(self.externalHostname))
        scoop.logger.debug('The python executable to execute the program with is: '
                     '{0}.'.format(self.python_executable))

        # Create launch lists
        self.broker_hosts = self.divideHosts(hosts[:], self.b)
        self.worker_hosts = self.divideHosts(hosts, self.n)

        # Logging of worker distribution warnings
        maximumWorkers = sum(host[1] for host in hosts)
        if self.n > maximumWorkers:
            scoop.logger.debug("The -n flag is set at {0} workers, which is higher "
                           "than the maximum number of workers ({1}) specified "
                           "by the hostfile.\nThis behavior may degrade the "
                           "performances of scoop for cpu-bound operations."
                           "".format(qty, maximumWorkers))
        elif self.n < maximumWorkers:
            scoop.logger.debug("The -n flag is set at {0} workers, which is lower "
                           "than the maximum number of workers ({1}) specified "
                           "by the hostfile."
                           "".format(qty, maximumWorkers))

        # Display
        self.showHostDivision(headless=not executable)

        self.workers = []
        self.brokers = []

    def initLogging(self):
        """Configures the logger."""
        verbose_levels = {
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG,
        }
        logging.basicConfig(
            level=verbose_levels[self.verbose],
            format="[%(asctime)-15s] %(module)-9s %(levelname)-7s %(message)s"
        )
        return logging.getLogger(self.__class__.__name__)

    def divideHosts(self, hosts, qty):
        """Divide processes among hosts."""
        maximumWorkers = sum(host[1] for host in hosts)

        # If specified amount of workers is greater than sum of each specified.
        if qty > maximumWorkers:
            index = 0
            while qty > maximumWorkers:
                hosts[index] = (hosts[index][0], hosts[index][1] + 1)
                index = (index + 1) % len(hosts)
                maximumWorkers += 1

        # If specified amount of workers if lower than sum of each specified.
        elif qty < maximumWorkers:
            
            while qty < maximumWorkers:
                maximumWorkers -= hosts[-1][1]
                if qty > maximumWorkers:
                    hosts[-1] = (hosts[-1][0], qty - maximumWorkers)
                    maximumWorkers += hosts[-1][1]
                else:
                    del hosts[-1]


        # Checking if the broker if externally routable
        if self.externalHostname in utils.loopbackReferences and \
                len(hosts) > 1 and \
                not self.tunnel:
            raise Exception("\n"
                            "Could not find route from external worker to the "
                            "broker: Unresolvable hostname or IP address.\n "
                            "Please specify your externally routable hostname "
                            "or IP using the --external-hostname parameter or "
                            " use the --tunnel flag.")

        hosts.reverse()
        return hosts

    def showHostDivision(self, headless):
        """Show the worker distribution over the hosts"""
        scoop.logger.info('Worker distribution: ')
        for worker, number in reversed(self.worker_hosts):
            first_worker = (worker == self.worker_hosts[-1][0])
            scoop.logger.info('   {0}:\t{1} {2}'.format(
                worker,
                number - 1 if first_worker or headless else str(number),
                "+ origin" if first_worker or headless else "",
                )
            )

    def _addWorker_args(self, workerinfo):
        """Create the arguments to pass to the addWorker call.
            The returned args and kwargs must ordered/named according to the namedtuple
            in LAUNCH_HOST_CLASS.LAUNCHING_ARGUMENTS

            both args and kwargs are supported for full flexibilty,
            but usage of kwargs only is strongly advised

            workerinfo is a dict with information that can be used to start the worker
        """
        args = []
        kwargs = {
            'pythonPath': self.pythonpath,
            'prolog': self.prolog,
            'path': self.path,
            'nice': self.nice,
            'pythonExecutable': self.python_executable,
            'size': self.n,
            'origin': self.workersLeft == 1,
            'brokerHostname': self.externalHostname,
            'brokerPorts': (self.brokers[0].brokerPort,
                            self.brokers[0].infoPort),
            'debug': self.debug,
            'profiling': self.profile,
            'executable': self.executable,
            'verbose': self.verbose,
            'backend': self.backend,
            'args': self.args,
        }
        return args, kwargs

    def addWorkerToHost(self, workerinfo):
        """Adds a worker to current host"""
        hostname = workerinfo['hostname']

        scoop.logger.debug('Initialising {0}{1} worker {2} [{3}].'.format(
            "local" if hostname in utils.localHostnames else "remote",
            " origin" if self.workersLeft == 1 else "",
            self.workersLeft,
            hostname,
            )
        )

        add_args, add_kwargs = self._addWorker_args(workerinfo)
        self.workers[-1].addWorker(*add_args, **add_kwargs)

    def run(self):
        """Launch the broker(s) and worker(s) assigned on every hosts."""
        # Launch the brokers
        for hostname, nb_brokers in self.broker_hosts:
            for ind in range(nb_brokers):
                # Launching the broker(s)
                if self.externalHostname in utils.localHostnames:
                    self.brokers.append(localBroker(
                        debug=self.debug,
                        nice=self.nice,
                        backend=self.backend,
                    ))
                else:
                    self.brokers.append(remoteBroker(
                        hostname=hostname,
                        pythonExecutable=self.python_executable,
                        debug=self.debug,
                        nice=self.nice,
                        backend=self.backend,
                    ))

        # Share connection information between brokers
        if self.b > 1:
            for broker in self.brokers:
                # Only send data of other brokers to a given broker
                connect_data = [
                    BrokerInfo(
                        x.getHost(),
                        *x.getPorts(),
                        externalHostname=x.getHost()
                    )
                    for x in self.brokers
                    if x is not broker
                ]
                broker.sendConnect(connect_data)

        # Launch the workers
        for hostname, nb_workers in self.worker_hosts:
            self.workers.append(self.LAUNCH_HOST_CLASS(hostname))
            total_workers_host = min(nb_workers, self.workersLeft)
            for worker_idx_host in range(total_workers_host):
                workerinfo = {
                    'hostname': hostname,
                    'total_workers_host': total_workers_host,
                    'worker_idx_host': worker_idx_host,
                }
                self.addWorkerToHost(workerinfo)
                self.workersLeft -= 1

            # Launch every workers at the same time
            scoop.logger.debug(
                "{0}: Launching '{1}'".format(
                    hostname,
                    self.workers[-1].getCommand(),
                )
            )
            shells = self.workers[-1].launch(
                (self.brokers[0].brokerPort,
                 self.brokers[0].infoPort)
                    if self.tunnel else None,
                stdPipe=not self.workers[-1].isLocal(),
            )
            if self.workersLeft <= 0:
                # We've launched every worker we needed, so let's exit the loop
                rootProcess = shells[-1]
                break

        # Wait for the root program
        if self.workers[-1].isLocal():
            self.errors = self.workers[-1].subprocesses[-1].wait()
        else:
            # Process stdout first, then the whole stderr at the end
            for outStream, inStream in [(sys.stdout, rootProcess.stdout),
                                        (sys.stderr, rootProcess.stderr)]:
                data = inStream.read(1)
                while len(data) > 0:
                    # Should not rely on utf-8 codec
                    outStream.write(data.decode("utf-8"))
                    outStream.flush()
                    data = inStream.read(1)
            self.errors = rootProcess.wait()
        scoop.logger.info('Root process is done.')
        return self.errors

    def close(self):
        """Subprocess cleanup."""
        # Give time to flush data if debug was on
        if self.debug:
            time.sleep(5)

        # Terminate workers
        for host in self.workers:
            host.close()

        # Terminate the brokers
        for broker in self.brokers:
            try:
                broker.close()
            except AttributeError:
                # Broker was not started (probably mislaunched)
                pass

        scoop.logger.info('Finished cleaning spawned subprocesses.')


def makeParser():
    """Create the SCOOP module arguments parser."""
    # TODO: Add environment variable (all + selection)
    parser = argparse.ArgumentParser(
        description="Starts a parallel program using SCOOP.",
        prog="{0} -m scoop".format(sys.executable),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--hosts', '--host',
                       help="The list of hosts. The first host will execute "
                            "the origin. (default is 127.0.0.1)",
                       metavar="Address",
                       nargs='*')
    group.add_argument('--hostfile',
                       help="The hostfile name",
                       metavar="FileName")
    parser.add_argument('--path', '-p',
                        help="The path to the executable on remote hosts "
                             "(default is local directory)",
                        default=os.getcwd())
    parser.add_argument('--nice',
                        type=int,
                        metavar="NiceLevel",
                        help="*nix niceness level (-20 to 19) to run the "
                             "executable")
    parser.add_argument('--verbose', '-v',
                        action='count',
                        help="Verbosity level of this launch script (-vv for "
                             "more)",
                        default=1)
    parser.add_argument('--quiet', '-q',
                        action='store_true')
    parser.add_argument('-n',
                        help="Total number of workers to launch on the hosts. "
                             "Workers are spawned sequentially over the hosts. "
                             "(ie. -n 3 with 2 hosts will spawn 2 workers on "
                             "the first host and 1 on the second.) (default: "
                             "Number of CPUs on current machine)",
                        type=int,
                        metavar="NumberOfWorkers")
    parser.add_argument('-b',
                        help="Total number of brokers to launch on the hosts. "
                             "Brokers are spawned sequentially over the hosts. "
                             "(ie. -b 3 with 2 hosts will spawn 2 brokers on "
                             "the first host and 1 on the second.) (default: "
                             "1)",
                        type=int,
                        default=1,
                        metavar="NumberOfBrokers")
    parser.add_argument('--tunnel',
                        help="Activate ssh tunnels to route toward the broker "
                             "sockets over remote connections (may eliminate "
                             "routing problems and activate encryption but "
                             "slows down communications)",
                        action='store_true')
    parser.add_argument('--external-hostname',
                        nargs=1,
                        help="The externally routable hostname / ip of this "
                             "machine. (defaults to the local hostname)",
                        metavar="Address")
    parser.add_argument('--python-interpreter',
                        nargs=1,
                        help="The python interpreter executable with which to "
                             "execute the script",
                        default=[sys.executable],
                        metavar="Path")
    parser.add_argument('--pythonpath',
                        nargs=1,
                        help="The PYTHONPATH environment variable (default is "
                             "current PYTHONPATH)",
                        default=[os.environ.get('PYTHONPATH', '')])
    parser.add_argument('--prolog',
                        nargs=1,
                        help="Absolute Path to a shell script or executable "
                             "that will be executed at the launch of every "
                             "worker",
                        default=[None])
    parser.add_argument('--debug',
                        help=argparse.SUPPRESS,
                        action='store_true')
    parser.add_argument('--profile',
                        help=("Turn on the profiling. SCOOP will call "
                        "cProfile.run on the executable for every worker and"
                        " will produce files in directory profile/ named "
                        "workerX where X is the number of the worker."),
                        action='store_true')
    parser.add_argument('--backend',
                        help="Choice of communication backend",
                        choices=['ZMQ', 'TCP'],
                        default='ZMQ')
    parser.add_argument('executable',
                        nargs='?',
                        help='The executable to start with SCOOP')
    parser.add_argument('args',
                        nargs=argparse.REMAINDER,
                        help='The arguments to pass to the executable',
                        default=[],
                        metavar="args")
    return parser


def main():
    """Execution of the SCOOP module. Parses its command-line arguments and
    launch needed resources."""
    # Generate a argparse parser and parse the command-line arguments
    parser = makeParser()
    args = parser.parse_args()

    # Get a list of resources to launch worker(s) on
    hosts = utils.getHosts(args.hostfile, args.hosts)
    if args.n:
        n = args.n
    else:
        n = utils.getWorkerQte(hosts)
    assert n > 0, ("Scoop couldn't determine the number of worker to start.\n"
                   "Use the '-n' flag to set it manually.")
    if not args.external_hostname:
        args.external_hostname = [utils.externalHostname(hosts)]

    # Launch SCOOP
    thisScoopApp = ScoopApp(hosts, n, args.b,
                            args.verbose if not args.quiet else 0,
                            args.python_interpreter,
                            args.external_hostname[0],
                            args.executable, args.args, args.tunnel,
                            args.path, args.debug, args.nice,
                            utils.getEnv(), args.profile, args.pythonpath[0],
                            args.prolog[0], args.backend)

    rootTaskExitCode = False
    interruptPreventer = Thread(target=thisScoopApp.close)
    try:
        rootTaskExitCode = thisScoopApp.run()
    except Exception as e:
        logging.error('Error while launching SCOOP subprocesses:')
        logging.error(traceback.format_exc())
        rootTaskExitCode = -1
    finally:
        # This should not be interrupted (ie. by a KeyboadInterrupt)
        # The only cross-platform way to do it I found was by using a thread.
        interruptPreventer.start()
        interruptPreventer.join()

    # Exit with the proper exit code
    if rootTaskExitCode:
        sys.exit(rootTaskExitCode)


if __name__ == "__main__":
    main()
