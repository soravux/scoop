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
from scoop import utils
from threading import Thread

class launchScoop(object):
    def __init__(self, hosts, n, verbose, python_executable, brokerHostname,
            executable, arguments, e, log, path, debug, nice, env, profile):
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
        self.profile = profile
        try:
            self.pythonpath = os.environ["PYTHONPATH"]
        except KeyError:
            self.pythonpaht = None


        # Logging configuration
        if self.verbose > 2:
            self.verbose = 2
        verbose_levels = {0: logging.WARNING,
                          1: logging.INFO,
                          2: logging.DEBUG}
        logging.basicConfig(filename=log,
                            level=verbose_levels[self.verbose],
                            format='[%(asctime)-15s] %(levelname)-7s %(message)s')
                            
        if env in ["PBS", "SGE"]:
            logging.info("Detected {0} environment.".format(env))
        logging.info("Deploying {0} workers over {1} "
                     "host(s).".format(n,
                                       len(hosts)))

        self.divideHosts(hosts)
     
        # Handling Broker Hostname
        self.brokerHostname = '127.0.0.1' if self.e else brokerHostname
        logging.debug('Using hostname/ip: "{0}" as external broker reference.'\
            .format(self.brokerHostname))
        logging.info('The python executable to execute the program with is: {0}.'\
            .format(self.python_executable))

   

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
            logging.info('Setting debug on')
            c.append("--debug")
        if self.profile == True:
            logging.info('Setting profile on')
            c.append("--profile")
        c.append(self.executable)
        c.extend(self.args)
        return c

    def launchForeign(self):
        pythonpath = "export PYTHONPATH={0} &&".format(self.pythonpath) if self.pythonpath else ''
        return ("{pythonpath} cd {remotePath} && {nice} {pythonExecutable} -m "
                "scoop.bootstrap.__main__ --workerName worker{workersLeft} "
                "--brokerName broker --brokerAddress tcp://{brokerHostname}:"
                "{brokerPort} --metaAddress tcp://{brokerHostname}:"
                "{infoPort} --size {n} {origin} {debug} {profile} {executable} "
                "{arguments}").format(remotePath = self.path, 
                    pythonpath = pythonpath,
                    nice = 'nice - n {0}'.format(self.nice) if self.nice != None else '',
                    origin = '--origin' if self.workersLeft == 1 else '',
                    debug = '--debug' if self.debug == 1 else '',
                    profile = '--profile' if self.profile == True else '',
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
        maximumWorkers = sum(host[1] for host in hosts)
        if self.n > maximumWorkers:
            logging.info("The -n flag is set at {0} workers, which is higher than\n"
                         "the maximum number of workers ({1}) specified by the hostfile.\n"
                         "This behaviour may degrade the performances of scoop for cpu-bound"
                         " operations.".format(self.n, sum(host[1] for host in hosts)))
        index = 0
        while self.n > maximumWorkers:
            hosts[index] = (hosts[index][0], hosts[index][1] + 1)
            index = (index + 1) % len(hosts)
            maximumWorkers += 1

        self.hosts = hosts

        # Show worker distribution
        if self.verbose > 1:
            logging.info('Worker distribution: ')
            for worker, number in self.hosts:
                logging.info('   {0}:\t{1} {2}'.format(
                    worker,
                    number - 1 if worker == hosts[0][0] else str(number),
                    "+ origin" if worker == hosts[0][0] else ""))
#
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
            for n in range(min(host[1], self.workersLeft)):
                logging.debug('Initialising {0}{1} worker {2} [{3}].'.format(
                    "local" if host[0] in ["127.0.0.1", "localhost"] else "remote",
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
            if len(command) != 0 :
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                if self.e:
                    ssh_command += [
                        '-R {0}:127.0.0.1:{0}'.format(self.brokerPort),
                        '-R {0}:127.0.0.1:{0}'.format(self.infoPort)]
                shell = subprocess.Popen(ssh_command + [
                    host[0],
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
                         "(defaults to the local hostname)")
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
parser.add_argument('--profile', help="Turn on the profiling",action='store_true')
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
    if len(hosts) == 1 and hosts[0][0] == "127.0.0.1":
        hosts = [("127.0.0.1", utils.getCPUcount())]
    if args.n:
        n = args.n
    else:
        n = utils.getWorkerQte(hosts)
    assert n > 0, ("Scoop couldn't determine the number of worker to start.\n"
                   "Use the '-n' flag to set it manually.")
    if args.broker_hostname:
        broker_hostname = args.broker_hostname
    else:
        broker_hostname = utils.broker_hostname(hosts)

    scoopLaunching = launchScoop(hosts, n, args.verbose,
            args.python_executable, broker_hostname, args.executable,
            args.args, args.e, args.log, args.path, args.debug, args.nice,
            utils.getEnv(), args.profile)
    try:
        scoopLaunching.run()
    finally:
        scoopLaunching.close()
