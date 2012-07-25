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
import argparse
import os
import sys
import socket
import subprocess
import time
import logging
from threading import Thread

class launchScoop(object):
    def __init__(self, hosts, n, verbose, python_executable, brokerHostname,
            executable, arguments, e, log, path, debug, nice):
        # Assure setup sanity
        assert type(hosts) == list and hosts != [], "You should at least specify one host."
        hosts.reverse()
        self.workersLeft = n
        self.createdSubprocesses = []

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
                            format='[%(asctime)-15s] %(levelname)-7s %(message)s')
        logging.info("Deploying {0} workers over {1} "
                     "host(s).".format(n,
                                       len(hosts)))

        self.divideHosts(hosts)
     
        # Handling Broker Hostname
        self.brokerHostname = '127.0.0.1' if self.e else brokerHostname[0]
        logging.debug('Using hostname/ip: "{0}" as external broker reference.'\
            .format(self.brokerHostname))
        logging.info('The python executable to execute the program with is: {0}.'\
            .format(self.python_executable))

   

    @property
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
                        "--size", str(self.n),
                        ]
        if self.workersLeft == 1:
            c.append("--origin")
        if self.debug == True:
            logging.debug('Set debug on')
            c.append("--debug")
        c.append(self.executable)
        c.extend(self.args)
        return c

    @property
    def launchForeign(self):
        return ("cd {remotePath} && {nice} {pythonExecutable} -m "
                "scoop.bootstrap.__main__ --workerName worker{workersLeft} "
                "--brokerName broker --brokerAddress tcp://{brokerHostname}:"
                "{brokerPort} --metaAddress tcp://{brokerHostname}:"
                "{infoPort} --size {n} {origin} {debug} {executable} "
                "{arguments}").format(remotePath = self.path, 
                    nice = 'nice - n {0}'.format(self.nice) if self.nice != None else '',
                    origin = '--origin' if self.workersLeft == 1 else '',
                    debug = '--debug' if self.debug == 1 else '',
                    pythonExecutable = self.python_executable,
                    workersLeft = self.workersLeft,
                    brokerHostname = self.brokerHostname,
                    brokerPort = self.brokerPort,
                    infoPort = self.infoPort,
                    n = self.n,
                    executable = self.executable,
                    arguments = " ".join(self.args))

    def divideHosts(self, hosts):
        """ Separe the workers accross hosts. """
        self.maximum_workers = {}
        if type(hosts[0]) == tuple:
            self.hosts = set(host[0] for host in hosts)
        else:
            self.hosts = set(hosts)
        if type(hosts[0]) == tuple:
            logging.debug("Using the hostfile to set the number of workers.")
            for host in hosts:
                self.maximum_workers[host[0]] = int(host[1])
        elif len(hosts) != len(self.hosts):
            logging.debug("Using amount of duplicates in self.hosts entry to "
                          "set the number of workers.")
            for host in hosts:
                self.maximum_workers[host] = hosts.count(host)
        else :
            # No duplicate entries in self.hosts found, division of workers 
            # pseudo-equally upon the self.hosts
            logging.debug('Dividing workers pseudo-equally over hosts')
            
            for index, host in enumerate(reversed(hosts)):
                self.maximum_workers[host] = (self.n // (len(self.hosts)) \
                    + int((self.n % len(self.hosts)) > index))

        # Show worker distribution
        if self.verbose > 1:
            logging.info('Worker distribution: ')
            for worker, number in self.maximum_workers.items():
                logging.info('   {0}:\t{1} {2}'.format(
                    worker,
                    number - 1 if worker == hosts[-1] else str(number),
                    "+ origin" if worker == hosts[-1] else ""))

    def startBroker(self):
        """Starts a broker on random unoccupied port(s)"""
        from scoop.broker import Broker
        self.localBroker = Broker(debug=True if self.debug == True else False)
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
        for host in self.hosts:
            command = []
            for n in range(min(self.maximum_workers[host], self.workersLeft)):
                logging.debug('Initialising {0}{1} worker {2} [{3}].'.format(
                    "local" if host in ["127.0.0.1", "localhost"] else "remote",
                    " origin" if self.workersLeft == 1 else "",
                    self.workersLeft,
                    host))
                if host in ["127.0.0.1", "localhost"]:
                    # Launching the workers
                    self.createdSubprocesses.append(
                        subprocess.Popen(self.launchLocal))
                else:
                    # If the host is remote, connect with ssh
                    command.append(self.launchForeign)
                self.workersLeft -= 1
            # Launch every remote hosts in the same time 
            if len(command) != 0 :
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                if self.e:
                    ssh_command += [
                        '-R {0}:127.0.0.1:{0}'.format(self.brokerPort),
                        '-R {0}:127.0.0.1:{0}'.format(self.infoPort)]
                shell = subprocess.Popen(ssh_command + [
                    host,
                    "bash -c '{0}; wait'".format(" & ".join(command))])
                self.createdSubprocesses.append(shell)
                command = []
            if self.workersLeft <= 0:
                # We've launched every worker we needed, so let's exit the loop!
                break
                
        # Ensure everything is started normaly
        for this_subprocess in self.createdSubprocesses:
            if this_subprocess.poll() is not None:
                raise Exception('Subprocess {0} terminated abnormaly.'\
                    .format(this_subprocess))
        
        # wait for the origin
        self.createdSubprocesses[-1].wait()

    def close(self):
        # Ensure everything is cleaned up on exit
        logging.debug('Destroying local elements...')
        self.createdSubprocesses.reverse() # Kill the broker last
        if self.debug == 1:
            # give time to flush data
            time.sleep(1)
        for process in self.createdSubprocesses:
            try:
                process.terminate()
            except OSError:
                pass
        logging.info('Finished destroying spawned subprocesses.')

def getHosts(filename):
    """Parse the hostfile to get number of slots. The hostfile must have
    the following structure :
    hostname  slots=X
    hostname2 slots=X
    """
    f = open(filename)
    hosts = [line.split() for line in f]
    f.close()
    return [(h[0], h[1].split("=")[1]) for h in hosts]

parser = argparse.ArgumentParser(description="Starts a parallel program using "
                                             "SCOOP.",
                                 prog="{0} -m scoop".format(sys.executable))
group = parser.add_mutually_exclusive_group()
group.add_argument('--hosts', '--host',
                    help="The list of hosts. The first host will execute the "
                         "origin. (default is 127.0.0.1)",
                    nargs='*',
                    default=["127.0.0.1"])
group.add_argument('--hostfile', help="The hostfile name")
parser.add_argument('--path', '-p',
                    help="The path to the executable on remote hosts  (default "
                         "is local directory)",
                    default=os.getcwd())
parser.add_argument('--nice',
                    type=int,
                    help="*nix niceness level (-20 to 19) to run the "
                         "executable")
parser.add_argument('--verbose', '-v',
                    action = 'count',
                    help = "Verbosity level of this launch script (-vv for "
                           "more)",
                    default = 0)
parser.add_argument('--log',
                    help = "The file to log the output. (default is stdout)",
                    default = None)
parser.add_argument('-n',
                    help="Total number of workers to launch on the hosts. "
                         "Workers are spawned sequentially over the hosts. "
                         "(ie. -n 3 with 2 hosts will spawn 2 workers on the "
                         "first host and 1 on the second.) (default: 1)",
                    type=int,
                    default=1)
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
                    default=[socket.getfqdn().split(".")[0]])
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
parser.add_argument('--debug', help="Turn on the debuging", action='store_true')
parser.add_argument('executable',
                    nargs=1,
                    help='The executable to start with SCOOP')
parser.add_argument('args',
                    nargs=argparse.REMAINDER,
                    help='The arguments to pass to the executable',
                    default=[])                   
args = parser.parse_args()
        
if __name__ == "__main__":
    if args.hostfile:
        hosts = getHosts(args.hostfile)
    else:
        hosts = args.hosts
    scoopLaunching = launchScoop(hosts, args.n, args.verbose,
            args.python_executable, args.broker_hostname, args.executable,
            args.args, args.e, args.log, args.path, args.debug, args.nice)
    try:
        scoopLaunching.run()
    finally:
        scoopLaunching.close()
