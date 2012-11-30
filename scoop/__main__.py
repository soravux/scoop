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
import argparse
import os
import sys
import socket
import subprocess
import time
import logging
from scoop import utils
from threading import Thread
import signal

try:
    signal.signal(signal.SIGQUIT, utils.KeyboardInterruptHandler)
except AttributeError:
    # SIGQUIT doesn't exist on Windows
    signal.signal(signal.SIGTERM, utils.KeyboardInterruptHandler)


class ScoopApp(object):
    def __init__(self, hosts, n, verbose, python_executable, brokerHostname,
            executable, arguments, tunnel, log, path, debug, nice, env, profile,
            pythonPath):
        # Assure setup sanity
        assert type(hosts) == list and hosts, ("You should at least "
                                               "specify one host.")
        self.workersLeft = n
        self.createdSubprocesses = []
        self.createdRemoteConn = {}

        # launch information
        self.python_executable = python_executable[0]
        self.pythonpath = pythonPath
        self.n = n
        self.tunnel = tunnel
        self.executable = executable[0]
        self.args = arguments
        self.verbose = verbose
        self.path = path
        self.debug = debug
        self.nice = nice
        self.profile = profile
        self.errors  = None


        # Logging configuration
        if self.verbose > 2:
            self.verbose = 2
        verbose_levels = {0: logging.WARNING,
                          1: logging.INFO,
                          2: logging.DEBUG}
        logging.basicConfig(filename=log,
                            level=verbose_levels[self.verbose],
                            format='[%(asctime)-15s] %(levelname)-7s '
                                   '%(message)s')

        if env in ["PBS", "SGE"]:
            logging.info("Detected {0} environment.".format(env))
        logging.info("Deploying {0} worker(s) over {1} "
                     "host(s).".format(n,
                                       len(hosts)))

        # Handling Broker Hostname
        self.brokerHostname = '127.0.0.1' if self.tunnel else brokerHostname
        logging.debug('Using hostname/ip: "{0}" as external broker '
                      'reference.'.format(self.brokerHostname))
        logging.info('The python executable to execute the program with is: '
                     '{0}.'.format(self.python_executable))

        self.divideHosts(hosts)

    def launchLocal(self):
        c = [self.python_executable,
             "-m", "scoop.bootstrap.__main__",
             "--workerName", "worker{0}".format(self.workersLeft),
             "--brokerName", "broker",
             "--brokerAddress",
             "tcp://{0}:{1}".format(self.brokerHostname,
                                    self.brokerPort),
             "--metaAddress",
             'tcp://{0}:{1}'.format(self.brokerHostname,
                                    self.infoPort),
             "--size", str(self.n)]
        if self.workersLeft == 1:
            c.append("--origin")
        if self.debug:
            logging.debug('Set debug on')
            c.append("--debug")
        if self.profile:
            logging.info('Setting profile on')
            c.append("--profile")
        c.append(self.executable)
        c.extend(self.args)
        return c

    def launchForeign(self):
        pythonpath = ("export PYTHONPATH={0} "
                      "&&".format(self.pythonpath) if self.pythonpath else '')
        return ("{pythonpath} cd {remotePath} && {nice} {pythonExecutable} -m "
                "scoop.bootstrap.__main__ --workerName worker{workersLeft} "
                "--brokerName broker --brokerAddress tcp://{brokerHostname}:"
                "{brokerPort} --metaAddress tcp://{brokerHostname}:"
                "{infoPort} --size {n} {origin} {debug} {profile} {executable} "
                "{arguments}").format(remotePath = self.path, 
                    pythonpath = pythonpath,
                    nice='nice -n {0}'.format(self.nice)
                    if self.nice is not None else '',
                    origin='--origin' if self.workersLeft == 1 else '',
                    debug='--debug' if self.debug else '',
                    profile='--profile' if self.profile else '',
                    pythonExecutable=self.python_executable,
                    workersLeft=self.workersLeft,
                    brokerHostname=self.brokerHostname,
                    brokerPort=self.brokerPort,
                    infoPort=self.infoPort,
                    n=self.n,
                    executable=self.executable,
                    arguments=" ".join(self.args))

    def divideHosts(self, hosts):
        """Divide the workers accross hosts."""
        maximumWorkers = sum(host[1] for host in hosts)

        # If specified amount of workers is greater than sum of each specified.
        if self.n > maximumWorkers:
            logging.info("The -n flag is set at {0} workers, which is higher "
                         "than the maximum number of workers ({1}) specified "
                         "by the hostfile.\nThis behaviour may degrade the "
                         "performances of scoop for cpu-bound operations."
                         "".format(self.n, maximumWorkers))
            index = 0
            while self.n > maximumWorkers:
                hosts[index] = (hosts[index][0], hosts[index][1] + 1)
                index = (index + 1) % len(hosts)
                maximumWorkers += 1

        # If specified amount of workers if lower than sum of each specified.
        elif self.n < maximumWorkers:
            logging.info("The -n flag is set at {0} workers, which is lower "
                         "than the maximum number of workers ({1}) specified "
                         "by the hostfile."
                         "".format(self.n, maximumWorkers))
            while self.n < maximumWorkers:
                maximumWorkers -= hosts[-1][1]
                if self.n > maximumWorkers:
                    hosts[-1] = (hosts[-1][0], self.n - maximumWorkers)
                    maximumWorkers += hosts[-1][1]
                else:
                    del hosts[-1]


        # Checking if the broker if externally routable
        if self.brokerHostname in ("127.0.0.1", "localhost", "::1") and \
                len(hosts) > 1 and \
                not self.tunnel:
            raise Exception("\n"
                            "Could not find route from external worker to the "
                            "broker: Unresolvable hostname or IP address.\n "
                            "Please specify your externally routable hostname "
                            "or IP using the --broker-hostname parameter.")

        hosts.reverse()
        self.hosts = hosts

        # Show worker distribution
        if self.verbose > 1:
            logging.info('Worker distribution: ')
            for worker, number in reversed(self.hosts):
                logging.info('   {0}:\t{1} {2}'.format(
                    worker,
                    number - 1 if worker == hosts[-1][0] else str(number),
                    "+ origin" if worker == hosts[-1][0] else ""))

    def startBroker(self):
        """Starts a broker on random unoccupied port(s)"""
        logging.debug("Starting the broker on host {0}".format(self.brokerHostname))
        if self.brokerHostname in utils.localHostnames:
            from scoop.broker import Broker
            self.localBroker = Broker(debug=self.debug)
            self.brokerPort, self.infoPort = self.localBroker.getPorts()
            self.localBrokerProcess = Thread(target=self.localBroker.run)
            self.localBrokerProcess.daemon = True
            self.localBrokerProcess.start()
            logging.debug("Local broker launched on ports {0}, {1}"
                          ".".format(self.brokerPort, self.infoPort))
        else:
            # TODO: Fusion with other remote launching
            # TODO: Populate self.createdRemoteConn
            brokerString = ("{pythonExec} -m scoop.broker.__main__ --tPort {brokerPort}"
                            " --mPort {infoPort}")
            for i in range(5000, 10000, 2):
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                broker = subprocess.Popen(ssh_command
                    + [self.brokerHostname]
                    + [brokerString.format(brokerPort=i,
                                           infoPort=i+1,
                                           pythonExec=self.python_executable)]
                )
                if broker.poll() is not None:
                    continue
                else:
                    self.brokerPort, self.infoPort = i, i+1
                    self.createdSubprocesses.append(broker)
                    break
            logging.debug("Foreign broker launched on ports {0}, {1} of host {2}"
                          ".".format(self.brokerPort, self.infoPort,
                              self.brokerHostname))

    def run(self):
        # Launching the local broker, repeat until it works
        logging.debug("Initialising local broker.")
        self.startBroker()

        # Launch the workers
        rootProcess="Local"
        for hostname, nbworkers in self.hosts:
            command = []
            for n in range(min(nbworkers, self.workersLeft)):
                logging.debug('Initialising {0}{1} worker {2} [{3}].'.format(
                    "local" if hostname in utils.localHostnames else "remote",
                    " origin" if self.workersLeft == 1 else "",
                    self.workersLeft,
                    hostname,
                    )
                )
                if hostname in utils.localHostnames:
                    # Launching the workers
                    self.createdSubprocesses.append(
                        subprocess.Popen(self.launchLocal())
                    )
                else:
                    # If the host is remote, connect with ssh
                    command.append(self.launchForeign())
                self.workersLeft -= 1
            # Launch every remote hosts in the same time
            if len(command) != 0:
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                if self.tunnel:
                    ssh_command += [
                        '-R {0}:127.0.0.1:{0}'.format(self.brokerPort),
                        '-R {0}:127.0.0.1:{0}'.format(self.infoPort)]
                shell = subprocess.Popen(ssh_command + [
                        hostname,
                        "bash -c 'ps -o pgid= -p $BASHPID && echo Poulet && {0} &'".format(
                            " & ".join(command))
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                )
                self.createdRemoteConn[shell] = [hostname]
                if self.workersLeft == 0:
                    rootProcess = shell
                command = []
            if self.workersLeft <= 0:
                # We've launched every worker we needed, so let's exit the loop
                break

        # Ensure everything is started normaly
        for thisSubprocess in self.createdSubprocesses:
            if thisSubprocess.poll() is not None:
                raise Exception('Subprocess {0} terminated abnormaly.'
                                .format(thisSubprocess))

        # Get group id from remote connections
        for thisRemote in self.createdRemoteConn.keys():
            GID = thisRemote.stdout.readline().strip()
            self.createdRemoteConn[thisRemote].append(GID)

        # Wait for the root program
        if rootProcess == "Local":
            self.errors = self.createdSubprocesses[-1].wait()
        else:
            # Process stdout first, then the whole stderr at the end
            for stream in [rootProcess.stdout, rootProcess.stderr]:
                data = stream.read(1)
                while len(data) > 0:
                    # Should not rely on utf-8 codec
                    # TODO: write stderr in sys.stderr
                    sys.stdout.write(data.decode("utf-8"))
                    sys.stdout.flush()
                    data = stream.read(1)
        # TODO: print others than root

    def close(self):
        # Ensure everything is cleaned up on exit
        logging.debug('Destroying local elements...')
        # Kill the broker last
        self.createdSubprocesses.reverse()
        if self.debug:
            # Give time to flush data
            time.sleep(5)
        for process in self.createdSubprocesses:
            try:
                process.terminate()
            except OSError:
                pass
        logging.debug('Destroying remote elements...')
        for shell, data in self.createdRemoteConn.items():
            if len(data) > 1:
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                subprocess.Popen(ssh_command + [
                    data[0],
                    "bash -c 'kill -9 -{0} &>/dev/null'".format(data[1])]).wait()
            else:
                logging.info('Zombie process left!')

        logging.info('Finished destroying spawned subprocesses.')
        exit(self.errors)

def makeParser():
    """Create the SCOOP module arguments parser."""
    parser = argparse.ArgumentParser(description="Starts a parallel program using "
                                                 "SCOOP.",
                                     prog="{0} -m scoop".format(sys.executable))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--hosts', '--host',
                       help="The list of hosts. The first host will execute the "
                            "origin. (default is 127.0.0.1)",
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
                        default=0)
    parser.add_argument('--log',
                        help="The file to log the output. (default is stdout)",
                        default=None,
                        metavar="FileName")
    parser.add_argument('-n',
                        help="Total number of workers to launch on the hosts. "
                             "Workers are spawned sequentially over the hosts. "
                             "(ie. -n 3 with 2 hosts will spawn 2 workers on the "
                             "first host and 1 on the second.) (default: Number of"
                             "CPUs on current machine)",
                        type=int,
                        metavar="NumberOfWorkers")
    parser.add_argument('--tunnel',
                        help="Activate ssh tunnels to route toward the broker "
                             "sockets over remote connections (may eliminate "
                             "routing problems and activate encryption but "
                             "slows down communications)",
                        action='store_true')
    parser.add_argument('--broker-hostname',
                        nargs=1,
                        help="The externally routable broker hostname / ip "
                             "(defaults to the local hostname)",
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
    parser.add_argument('--debug',
                        help=argparse.SUPPRESS,
                        action='store_true')
    parser.add_argument('--profile',
                        help=("Turn on the profiling. SCOOP will call cProfile.run\n"
                        "on the executable for every worker and will produce files\n"
                        "named workerX where X is the number of the worker."),
                        action='store_true')
    parser.add_argument('executable',
                        nargs=1,
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
    if not args.broker_hostname:
        args.broker_hostname = [utils.brokerHostname(hosts)]

    # Launch SCOOP
    scoopApp = ScoopApp(hosts, n, args.verbose,
                        args.python_interpreter,
                        args.broker_hostname[0],
                        args.executable, args.args, args.tunnel,
                        args.log, args.path, args.debug, args.nice,
                        utils.getEnv(), args.profile,
                        args.pythonpath[0])
    try:
        rootTaskExitCode = scoopApp.run()
    except Exception as e:
        print('Error while launching SCOOP subprocesses: {0}'.format(e))
    finally:
        scoopApp.close()
    exit(rootTaskExitCode)


if __name__ == "__main__":
    main()