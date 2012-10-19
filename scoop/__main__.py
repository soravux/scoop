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


class launchScoop(object):
    def __init__(self, hosts, n, verbose, python_executable, brokerHostname,
                 executable, arguments, e, log, path, debug, nice, env):
        # Assure setup sanity
        assert type(hosts) == list and hosts != [], ("You should at least "
                                                     "specify one host.")
        self.workersLeft = n
        self.createdSubprocesses = []
        self.createdRemoteConn = {}

        # launch information
        self.python_executable = python_executable[0]
        self.n = n
        self.e = e
        self.executable = executable[0]
        self.args = arguments
        self.verbose = verbose
        self.path = path
        self.debug = debug
        self.nice = nice

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
        self.brokerHostname = '127.0.0.1' if self.e else brokerHostname[0]
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
        if self.debug is True:
            logging.debug('Set debug on')
            c.append("--debug")
        c.append(self.executable)
        c.extend(self.args)
        return c

    def launchForeign(self):
        return ("cd {remotePath} && {nice} {pythonExecutable} -m "
                "scoop.bootstrap.__main__ --workerName worker{workersLeft} "
                "--brokerName broker --brokerAddress tcp://{brokerHostname}:"
                "{brokerPort} --metaAddress tcp://{brokerHostname}:"
                "{infoPort} --size {n} {origin} {debug} {executable} "
                "{arguments}").format(
                    remotePath=self.path,
                    nice='nice -n {0}'.format(self.nice)
                    if self.nice is not None else '',
                    origin='--origin' if self.workersLeft == 1 else '',
                    debug='--debug' if self.debug == 1 else '',
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
                         "".format(self.n, sum(host[1] for host in hosts)))
        index = 0
        while self.n > maximumWorkers:
            hosts[index] = (hosts[index][0], hosts[index][1] + 1)
            index = (index + 1) % len(hosts)
            maximumWorkers += 1

        # If specified amount of workers if lower than sum of each specified.
        if self.n < maximumWorkers:
            logging.info("The -n flag is set at {0} workers, which is lower "
                         "than the maximum number of workers ({1}) specified "
                         "by the hostfile."
                         "".format(self.n, sum(host[1] for host in hosts)))
        while self.n < maximumWorkers:
            if hosts[-1][1] > maximumWorkers - self.n:
                hosts[-1] = (hosts[-1][0],
                             hosts[-1][1] - (maximumWorkers - self.n))
            else:
                del hosts[-1]
            maximumWorkers = sum(host[1] for host in hosts)

        # Checking if the broker if externally routable
        if self.brokerHostname in ["127.0.0.1", "localhost"] and \
                len(hosts) > 1 and \
                self.e is not True:
            raise Exception("\n"
                            "Could not find route from external worker to the "
                            "broker: Unresolvable hostname or IP address.\n "
                            "Please specify your externally routable hostname "
                            "or IP using the --broker-hostname parameter.")

        hosts.reverse()
        self.hosts = hosts

        # Show worker distribution
        nbWorkers = 0
        if self.verbose > 1:
            logging.info('Worker distribution: ')
            for worker, number in reversed(self.hosts):
                logging.info('   {0}:\t{1} {2}'.format(
                    worker,
                    number - 1 if worker == hosts[-1][0] else str(number),
                    "+ origin" if worker == hosts[-1][0] else ""))

    def startBroker(self):
        """Starts a broker on random unoccupied port(s)"""
        from scoop.broker import Broker
        self.localBroker = Broker(debug=True if self.debug is True else False)
        self.brokerPort, self.infoPort = self.localBroker.getPorts()
        self.localBrokerProcess = Thread(target=self.localBroker.run)
        self.localBrokerProcess.daemon = True
        self.localBrokerProcess.start()

    def run(self):
        # Launching the local broker, repeat until it works
        logging.debug("Initialising local broker.")
        self.startBroker()
        logging.debug("Local broker launched on ports {0}, {1}"
                      ".".format(self.brokerPort, self.infoPort))

        # Launch the workers
        rootProcess="Local"
        for host in self.hosts:
            command = []
            for n in range(min(host[1], self.workersLeft)):
                logging.debug('Initialising {0}{1} worker {2} [{3}].'.format(
                    "local" if host[0] in ["127.0.0.1", "localhost"]
                    else "remote",
                    " origin" if self.workersLeft == 1 else "",
                    self.workersLeft,
                    host[0]))
                if host[0] in ["127.0.0.1", "localhost"]:
                    # Launching the workers
                    self.createdSubprocesses.append(
                        subprocess.Popen(self.launchLocal()))
                else:
                    # If the host is remote, connect with ssh
                    command.append(self.launchForeign())
                self.workersLeft -= 1
            # Launch every remote hosts in the same time
            if len(command) != 0:
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                if self.e:
                    ssh_command += [
                        '-R {0}:127.0.0.1:{0}'.format(self.brokerPort),
                        '-R {0}:127.0.0.1:{0}'.format(self.infoPort)]
                shell = subprocess.Popen(ssh_command + [
                    host[0],
                    "bash -c 'ps -o pgid= -p $BASHPID && {0} &'".format(" & ".join(command))],
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE)
                self.createdRemoteConn[shell] = [host[0]]
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
            return self.createdSubprocesses[-1].wait()
        else:
            data = rootProcess.stdout.read(1)
            while len(data) > 0:
                sys.stdout.write(data)
                data = rootProcess.stdout.read(1)

    def close(self):
        # Ensure everything is cleaned up on exit
        logging.debug('Destroying local elements...')
        # Kill the broker last
        self.createdSubprocesses.reverse()
        if self.debug == 1:
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

parser = argparse.ArgumentParser(description="Starts a parallel program using "
                                             "SCOOP.",
                                 prog="{0} -m scoop".format(sys.executable))
group = parser.add_mutually_exclusive_group()
group.add_argument('--hosts', '--host',
                   help="The list of hosts. The first host will execute the "
                        "origin. (default is 127.0.0.1)",
                   nargs='*')
group.add_argument('--hostfile', help="The hostfile name")
parser.add_argument('--path', '-p',
                    help="The path to the executable on remote hosts "
                         "(default is local directory)",
                    default=os.getcwd())
parser.add_argument('--nice',
                    type=int,
                    help="*nix niceness level (-20 to 19) to run the "
                         "executable")
parser.add_argument('--verbose', '-v',
                    action='count',
                    help="Verbosity level of this launch script (-vv for "
                           "more)",
                    default=0)
parser.add_argument('--log',
                    help="The file to log the output. (default is stdout)",
                    default=None)
parser.add_argument('-n',
                    help="Total number of workers to launch on the hosts. "
                         "Workers are spawned sequentially over the hosts. "
                         "(ie. -n 3 with 2 hosts will spawn 2 workers on the "
                         "first host and 1 on the second.) (default: Number of"
                         "CPUs on current machine)",
                    type=int)
parser.add_argument('-e',
                    help="Activate ssh tunnels to route toward the broker "
                         "sockets over remote connections (may eliminate "
                         "routing problems and activate encryption but "
                         "slows down communications)",
                    action='store_true')
parser.add_argument('--broker-hostname',
                    nargs=1,
                    help="The externally routable broker hostname / ip "
                         "(defaults to the local hostname)",
                    default=[utils.getCurrentHostname()])
parser.add_argument('--python-executable',
                    nargs=1,
                    help="The python executable with which to execute the "
                         "script",
                    default=[sys.executable])
parser.add_argument('--pythonpath',
                    nargs=1,
                    help="The PYTHONPATH environment variable (default is "
                         "current PYTHONPATH)",
                    default=[os.environ.get('PYTHONPATH', '')])
parser.add_argument('--debug',
                    help="Turn on the debuging",
                    action='store_true')
parser.add_argument('executable',
                    nargs=1,
                    help='The executable to start with SCOOP')
parser.add_argument('args',
                    nargs=argparse.REMAINDER,
                    help='The arguments to pass to the executable',
                    default=[])
args = parser.parse_args()

if __name__ == "__main__":
    hosts = utils.getHosts(args.hostfile, args.hosts)
    if args.n:
        n = args.n
    else:
        n = utils.getWorkerQte(hosts)
    assert n > 0, ("Scoop couldn't determine the number of worker to start.\n"
                   "Use the '-n' flag to set it manually.")
    scoopLaunching = launchScoop(hosts, n, args.verbose,
                                 args.python_executable, args.broker_hostname,
                                 args.executable, args.args, args.e, args.log,
                                 args.path, args.debug, args.nice,
                                 utils.getEnv())
    try:
        code = scoopLaunching.run()
    finally:
        scoopLaunching.close()
    exit(code)
