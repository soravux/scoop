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
import subprocess
import argparse
import time
import os
import sys
import socket
import random
import logging
    
parser = argparse.ArgumentParser(description='Starts a parallel program using SCOOP.',
                                 fromfile_prefix_chars='@',
                                 prog="{0} -m scoop".format(sys.executable))
parser.add_argument('--hosts', '--host',
                    help="The list of hosts. The first host will execute the "
                         "origin.",
                    nargs='*',
                    default=["127.0.0.1"])
parser.add_argument('--path', '-p',
                    help="The path to the executable on remote hosts",
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
                    help = "The file to log the output (default is stdout)",
                    default = None)
parser.add_argument('-n',
                    help="Number of process to launch the executable with",
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
                    help="The PYTHONPATH environment variable",
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

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
def port_ready(port):
    """Checks if a given port is already binded"""
    try:
        s.connect(('127.0.0.1', port))
    except IOError:
        return False
    else:
        s.shutdown(2)
        return True

class launchScoop(object):
    def __init__(self):
        # Assure setup sanity
        assert type(args.hosts) == list and args.hosts != [], "You should at least specify one host."
        args.hosts.reverse()
        self.hosts = set(args.hosts)
        self.workers_left = args.n
        self.created_subprocesses = []
        
        # Logging configuration
        if args.verbose > 2:
            args.verbose = 2
        verbose_levels = {0: logging.WARNING,
                          1: logging.INFO,
                          2: logging.DEBUG}
        logging.basicConfig(filename=args.log,
                            level=verbose_levels[args.verbose],
                            format='[%(asctime)-15s] %(levelname)-7s %(message)s')
        logging.info('Deploying {0} workers over {1} host(s).'.format(args.n, len(self.hosts)))

        self.divideHosts()
    
    @property
    def launchLocal(self):
        c = [args.python_executable[0],
                        "-m", "scoop.bootstrap",
                        "--workerName", "worker{}".format(self.workers_left),
                        "--brokerName", "broker",
                        "--brokerAddress",
                        "tcp://{0}:{1}".format(args.broker_hostname,
                                               self.broker_port),
                        "--metaAddress",
                        'tcp://{0}:{1}'.format(args.broker_hostname,
                                               self.info_port),
                        "--size", str(args.n),
                        ]
        if self.workers_left == 1:
            c.append("--origin")
        c.append(args.executable[0])
        c.extend(args.args)
        return c

    @property
    def launchForeign(self):
        return "cd {remotePath} && {nice} {pythonExecutable} -m\
scoop.bootstrap --workerName worker{workers_left} --brokerName \
broker --brokerAddress tcp://{broker_hostname}:{broker_port} \
--metaAddress tcp://{broker_hostname}:{info_port} --size {n} \
{origin} {executable}\
{arguments}".format(remotePath = args.path, 
                    nice = 'nice - n {}'.format(args.nice) if args.nice != None else '',
                    origin = '--origin' if self.workers_left == 1 else '',
                    pythonExecutable = args.python_executable[0],
                    workers_left = self.workers_left,
                    broker_hostname = args.broker_hostname,
                    broker_port = self.broker_port,
                    info_port = self.info_port,
                    n = args.n,
                    executable = args.executable[0],
                    arguments = " ".join(args.args))


    def divideHosts(self):
        """ Separe the workers accross hosts. """
        self.maximum_workers = {}
        if len(args.hosts) != len(self.hosts):
            logging.debug('Using amount of duplicates in self.hosts entry to set the number of workers.')
            for host in args.hosts:
                self.maximum_workers[host] = args.hosts.count(host)
        else :
            # No duplicate entries in self.hosts found, division of workers pseudo-equally
            # upon the self.hosts
            logging.debug('Dividing workers pseudo-equally over hosts')
            
            for index, host in enumerate(reversed(args.hosts)):
                self.maximum_workers[host] = (args.n // (len(self.hosts)) \
                    + int((args.n % len(self.hosts)) > index))

        # Show worker distribution
        if args.verbose > 1:
            logging.info('Worker distribution: ')
            for worker, number in self.maximum_workers.items():
                logging.info('   {0}:\t{1} {2}'.format(
                    worker,
                    number - 1 if worker == args.hosts[-1] else str(number),
                    "+ origin" if worker == args.hosts[-1] else ""))

        # Handling Broker Hostname
        args.broker_hostname = '127.0.0.1' if args.e else args.broker_hostname[0]
        logging.debug('Using hostname/ip: "{0}" as external broker reference.'\
            .format(args.broker_hostname))
        logging.info('The python executable to execute the program with is: {0}.'\
            .format(args.python_executable[0]))



    def startBroker(self):
        """Starts a broker on random unoccupied port(s)"""
        # Check if port is not already in use
        while True:
            broker_port = random.randint(1025, 49151)
            if not any(map(port_ready, [broker_port, broker_port + 1])):
                break

        # Spawn the broker
        broker_subproc = subprocess.Popen([args.python_executable[0],
                "-m", "scoop.broker", "--tPort",str(broker_port),"--mPort", str(broker_port + 1)])

        # Let's wait until the local broker is up and running...
        begin = time.time()
        while(time.time() - begin < 10.0):
            time.sleep(0.1)
            if port_ready(broker_port):
                break
        else:
            broker_subproc.kill()
            raise IOError('Could not start server!')
        
        self.broker_subproc = broker_subproc
        self.broker_port = broker_port
        self.info_port = broker_port + 1
        return (broker_port, broker_port + 1)
    
    def run(self):
        # Launching the local broker, repeat until it works
        logging.debug('Initialising local broker.')
        while True:
            try:
                broker_port, info_port = self.startBroker()
                if self.broker_subproc.poll() != None:
                    # Check if the process already returned (It shouldn't
                    # have). Retry if it did.
                    continue
                self.created_subprocesses.append(self.broker_subproc)
                break
            except IOError:
                continue
        logging.debug('Local broker launched on ports {0}, {1}.'.format(broker_port, info_port))
        
        # Launch the workers
        for host in args.hosts:
            command = []
            for n in range(min(self.maximum_workers[host], self.workers_left)):


                logging.debug('Initialising {0}{1} worker {2} [{3}].'.format(
                    "local" if host in ["127.0.0.1", "localhost"] else "remote",
                    " origin" if self.workers_left == 1 else "",
                    self.workers_left,
                    host))
                if host in ["127.0.0.1", "localhost"]:
                    # Launching the workers
                    self.created_subprocesses.append(subprocess.Popen(self.launchLocal))
                else:
                    # If the host is remote, connect with ssh
                    command.append(self.launchForeign)
                self.workers_left -= 1
            # Launch every remote hosts in the same time 
            if len(command) != 0 :
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                if args.e:
                            ssh_command += ['-R {0}:127.0.0.1:{0}'.format(self.broker_port),
                                            '-R {0}:127.0.0.1:{0}'.format(self.info_port)]
                shell = subprocess.Popen(ssh_command + [
                    host,
                    "bash -c '{0}; wait'".format(" & ".join(command))])
                self.created_subprocesses.append(shell)
                command = []
            if self.workers_left <= 0:
                # We've launched every worker we needed, so let's exit the loop!
                break
                
        # Ensure everything is started normaly
        for this_subprocess in self.created_subprocesses:
            if this_subprocess.poll() is not None:
                raise Exception('Subprocess {0} terminated abnormaly.'\
                    .format(this_subprocess))
        
        # wait for the origin
        self.created_subprocesses[-1].wait()



    def close(self):
        # Ensure everything is cleaned up on exit
        logging.debug('Destroying local elements of the federation...')
        self.created_subprocesses.reverse() # Kill the broker last
        if args.debug == 1:
            # give time to flush data
            time.sleep(1)
        for process in self.created_subprocesses:
            try:
                process.terminate()
            except OSError:
                pass
        logging.info('Finished destroying spawned subprocesses.')
   
scoopLaunching = launchScoop()
try:
    scoopLaunching.run()
finally:
    scoopLaunching.close()
