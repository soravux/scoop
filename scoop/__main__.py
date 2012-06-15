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
import scoop
import socket
import random
import logging
    
parser = argparse.ArgumentParser(description='Starts the executable on the nodes.',
                                 fromfile_prefix_chars='@',
                                 prog="{0} -m scoop".format(sys.executable))
parser.add_argument('--hosts', '--host',
                    help="A file containing a list of hosts. The first host "
                         "will execute the origin.",
                    nargs='*',
                    default=["127.0.0.1"])
parser.add_argument('--path', '-p',
                    help="The path to the executable on remote hosts",
                    default=os.getcwd())
parser.add_argument('--nice',
                    type=int,
                    help="UNIX niceness level (-20 to 19) to run the "
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
                         "script (with absolute path if necessary)",
                    default=[sys.executable])
parser.add_argument('--pythonpath',
                    nargs=1,
                    help="The PYTHONPATH environment variable",
                    default=[os.environ.get('PYTHONPATH', '')])
parser.add_argument('executable',
                    nargs=1,
                    help='The executable to start with scoop')
parser.add_argument('args',
                    nargs=argparse.REMAINDER,
                    help='The arguments to pass to the executable',
                    default=[])
args = parser.parse_args()



# String passed to the python interpreter to bootstrap the process and launch
# the interpreter with the user's module.

localBootstrap = """from scoop.futures import _startup
import runpy, sys, functools
sys.path.append(r"{programPath}")
from {basename} import *
sys.argv += {arguments}
_startup(functools.partial(runpy.run_path, '{executable}',init_globals=globals(), run_name='__main__'))
"""

# String passed to bash throught ssh to the foreign members of the working group.

foreignBootstrap = """cd {remotePath} && {envVars} {nice} {pythonExecutable} -c "from scoop.futures import _startup
import runpy, sys, functools
sys.path.append(r\\"{programPath}\\")
from {basename} import *
sys.argv += {remoteArguments}
_startup(functools.partial(runpy.run_path, \\"{executable}\\",
init_globals=globals(), run_name=\\"__main__\\"))" """

# Dictionary to format the localBootstrap and foreignBootstrap strings.

arguments = {'executable': args.executable[0],
             'arguments': str(args.args),
             'remoteArguments': str(args.args).replace("'", '\\"'),
             'basename': os.path.basename(args.executable[0])[:-3],
             'programPath': os.path.join(args.path, os.path.dirname(args.executable[0])).replace("\\", "/"),
             'remotePath': args.path,
             'nice': ('','nice -n {}'.format(args.nice))[args.nice != None],
             'pythonExecutable': args.python_executable[0],
             'envVars': []}


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

        self.maximum_workers = {}
        # If multiple times the same host in argument, it means that the maximum number
        # of workers has been setted by the number of times it is in the array
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

        # Backup the environment for future restore
        self.backup_environ = os.environ.copy()

    def startBroker(self):
        """Starts a broker on random unoccupied port(s)"""
        # Find the broker
        # TODO: _broker.py
        from scoop.broker import Broker
        
        # Check if port is not already in use
        while True:
            broker_port = random.randint(1025, 49151)
            if not any(map(port_ready, [broker_port, broker_port + 1])):
                break
        
        # Spawn the broker
        broker_subproc = subprocess.Popen([args.python_executable[0],
                os.path.abspath(sys.modules[Broker.__module__].__file__),
                str(broker_port), str(broker_port + 1)])
            
        # Let's wait until the local broker is up and running...
        begin = time.time()
        while(time.time() - begin < 10.0):
            time.sleep(0.1)
            if port_ready(broker_port):
                break
        else:
            broker_subproc.kill()
            raise IOError('Could not start server!')
            
        return (broker_subproc, broker_port, broker_port + 1)
    
    def run(self):
        # Launching the local broker, repeat until it works
        logging.debug('Initialising local broker.')
        while True:
            try:
                broker_subproc, broker_port, info_port = self.startBroker()
                if broker_subproc.poll() != None:
                    continue
                self.created_subprocesses.append(broker_subproc)
                break
            except IOError:
                continue
        logging.debug('Local broker launched on ports {0}, {1}.'.format(broker_port, info_port))
        
        # Launch the workers
        for host in args.hosts:
            command = []
            for n in range(min(self.maximum_workers[host], self.workers_left)):
                # Setting up environment variables
                env_vars = {'IS_ORIGIN': '0' if self.workers_left > 1 else '1',
                            'WORKER_NAME': 'worker{0}'.format(self.workers_left),
                            'BROKER_NAME': 'broker',
                            'BROKER_ADDRESS': 'tcp://{0}:{1}'.format(
                                args.broker_hostname,
                                broker_port),
                            'META_ADDRESS': 'tcp://{0}:{1}'.format(
                                args.broker_hostname,
                                info_port),
                            'SCOOP_DEBUG': '1' if scoop.DEBUG else '0',
                            'PYTHONPATH': args.pythonpath[0],}

                arguments['envVars'] = " ".join([key + "=" + value for key, value in env_vars.items()])


                logging.debug('Initialising {0}{1} worker {2} [{3}].'.format(
                    "local" if host in ["127.0.0.1", "localhost"] else "remote",
                    " origin" if env_vars['IS_ORIGIN'] == '1' else "",
                    self.workers_left,
                    host))
                if host in ["127.0.0.1", "localhost"]:
                    # Launching the workers
                    os.environ.update(env_vars)
                    self.created_subprocesses.append(subprocess.Popen([args.python_executable[0],
                    "-c",
                    localBootstrap.format(**arguments)]))
                else:
                    # If the host is remote, connect with ssh
                    command.append(foreignBootstrap.format(**arguments))
                self.workers_left -= 1
            # Launch every remote hosts in the same time 
            if len(command) != 0 :
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                if args.e:
                            ssh_command += ['-R {0}:127.0.0.1:{0}'.format(broker_port),
                                            '-R {0}:127.0.0.1:{0}'.format(info_port)]
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
        if scoop.DEBUG == 1:
            # give time to flush data
            time.sleep(1)
        for process in self.created_subprocesses:
            try:
                process.terminate()
            except OSError:
                pass
        logging.info('Finished destroying spawned subprocesses.')
        os.environ = self.backup_environ
        logging.info('Restored environment variables.')

    
scoopLaunching = launchScoop()
try:
    scoopLaunching.run()
finally:
    scoopLaunching.close()
