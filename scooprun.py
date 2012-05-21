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

def log(text, level=0):
    """Easily logs on screen the different events happening based on the
    verbosity level"""
    if args.verbose > level-1:
        print("[{0}]\t{2} -> {1}".format(time.time(), text, __file__))

cwd = os.getcwd()
    
parser = argparse.ArgumentParser(description='Starts the executable on the nodes.',
                                 fromfile_prefix_chars='@')
parser.add_argument('--hosts', '--host',
                    help='A file containing a list of hosts',
                    nargs='*',
                    default=["127.0.0.1"])
parser.add_argument('--path', '-p',
                    help="The path to the executable on remote hosts",
                    default=cwd)
parser.add_argument('--nice',
                    type=int,
                    help="Nice level")
parser.add_argument('--verbose', '-v',
                    action='count',
                    help="Verbosity level",
                    default=0)
parser.add_argument('-N',
                    help="Number of process",
                    type=int,
                    default=1)
parser.add_argument('-e',
                    help="Activate encryption on broker sockets over remote connections(may eliminate routing problems)",
                    action='store_true')
parser.add_argument('executable',
                    nargs='+',
                    help='The executable to start with scoop and its arguments')
parser.add_argument('--broker-hostname',
                    nargs=1,
                    help='The broker hostname (from outside)')
parser.add_argument('--python-executable',
                    nargs=1,
                    help='The python executable with which to execute the script (including path if necessary)',
                    default=[sys.executable])
args = parser.parse_args()

assert type(args.hosts) == list and args.hosts != [], "You should at least specify one host."
args.hosts.reverse()
hosts = set(args.hosts)
raw_hosts = args.hosts[:]
workers_left = args.N
created_subprocesses = []

log('Deploying {0} workers over {1} host(s).'.format(args.N, len(hosts)), 2)

maximum_workers = {}
# If multiple times the same host in argument, it means that the maximum number
# of workers has been setted by the number of times it is in the array
if len(raw_hosts) != len(hosts):
    log('Using amount of duplicates in hosts entry to set the number of workers.',
        1)
    for host in hosts:
        maximum_workers[host] = raw_hosts.count(host)
else :
    # No duplicate entries in hosts found, division of workers pseudo-equally
    # upon the hosts
    log('Dividing workers pseudo-equally over hosts', 1)
    for index, host in enumerate(hosts):
        maximum_workers[host] = (args.N / (len(hosts)) \
                                + int((args.N % len(hosts)) > index))
log('Worker distribution: {0}'.format(maximum_workers), 2)
                                
# Get the externally routable local hostname
if args.broker_hostname == None:
    broker_hostname = socket.gethostname()
else:
    broker_hostname = args.broker_hostname[0]
log('Using hostname/ip: "{0}" as external broker reference.'\
    .format(broker_hostname), 1)

try:
    # Launching the local broker
    log('Initialising local broker.', 1)
    
    # Find the broker
    from broker import Broker

    created_subprocesses.append(subprocess.Popen([args.python_executable[0],
        os.path.abspath(sys.modules[Broker.__module__].__file__)]))
        
    # Let's wait until the local broker is up and running...
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    begin = time.time()
    while(time.time() - begin < 10.0):
        time.sleep(0.1)
        try:
            s.connect(('127.0.0.1', 5555))
            s.shutdown(2)
            break
        except:
            pass
    else:
        raise Exception('Could not start server!')
            
    # Launch the workers
    for index, host in enumerate(hosts):
        if host in ["127.0.0.1", "localhost"]:
            # Launching the workers
            log('Initialising local workers attached to the local broker...', 1)
            for n in range(min(maximum_workers['127.0.0.1'], workers_left - 1)):
                log('Initialising local worker {0}.'.format(n), 2)
                os.environ.update({'WORKER_NAME': 'worker{0}'.format(n),
                                   'IS_ORIGIN': '0'})
                created_subprocesses.append(subprocess.Popen([args.python_executable[0]] \
                    + args.executable))
                workers_left -= 1
        else:
            # If the host is remote, connect with ssh
            port_redir_done = False
            log('Initialising remote workers of host {0} attached to the local broker...'.format(host), 1)
            for a in range(min(maximum_workers.get(host, 1), workers_left - 1)):
                log('Initialising remote worker {0}'.format(workers_left), 2)
                command = 'bash -c \'PYTHONPATH={4} \
IS_ORIGIN=0 \
WORKER_NAME=worker{2} \
BROKER_NAME=broker \
BROKER_ADDRESS=tcp://{1}:5555 \
META_ADDRESS=tcp://{1}:5556; cd {6} && {5} {3} {0}\''.format(
                    " ".join(args.executable),
                    '127.0.0.1' if args.e else broker_hostname,
                    workers_left,
                    args.python_executable[0],
                    os.environ.get("PYTHONPATH", "$PYTHONPATH"),
                    ('', 'nice -n {0}'.format(args.nice))[args.nice != None],
                    args.path)
                # TODO: start every worker in one SSH channel.
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                if args.e and port_redir_done == False:
                    ssh_command += ['-R 5555:127.0.0.1:5555', '-R 5556:127.0.0.1:5556']
                    port_redir_done = True
                shell = subprocess.Popen(ssh_command + [host,
                                                        command])
                created_subprocesses.append(shell)
                workers_left -= 1
        if workers_left <= 1:
            # We've launched every worker we needed, so let's exit the loop!
            break
        
    # Ensure everything is started normaly
    for this_subprocess in created_subprocesses:
        if this_subprocess.poll() is not None:
            raise Exception('Subprocess {0} terminated abnormaly.'\
                .format(this_subprocess))
    
    # Everything has been started everywhere, we can then launch our origin on
    # the first host stated.
    if host in ["127.0.0.1", "localhost"]:
        log('Initialising local origin.', 1)
        os.environ.update({'WORKER_NAME': 'root',
                           'IS_ORIGIN': '1'})
        created_subprocesses.append(subprocess.call([args.python_executable[0]] + args.executable))
    else:
        log('Initialising remote worker {0}'.format(workers_left), 2)
        command = 'bash -c \'PYTHONPATH={4} \
IS_ORIGIN=0 \
WORKER_NAME=worker{2} \
BROKER_NAME=broker \
BROKER_ADDRESS=tcp://{1}:5555 \
META_ADDRESS=tcp://{1}:5556; cd {6} && {5} {3} {0}\''.format(
            " ".join(args.executable),
            '127.0.0.1' if args.e else broker_hostname,
            workers_left,
            args.python_executable[0],
            os.environ.get("PYTHONPATH", "$PYTHONPATH"),
            ('', 'nice -n {0}'.format(args.nice))[args.nice != None],
            args.path)
        # TODO: start every worker in one SSH channel.
        ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
        if args.e:
            ssh_command += ['-R 5555:127.0.0.1:5555', '-R 5556:127.0.0.1:5556']
        shell = subprocess.call(ssh_command + [host,
                                               command])
    
finally:
    # Ensure everything is cleaned up on exit
    log('Destroying local elements of the federation...', 1)
    for process in created_subprocesses:
        try: process.terminate()
        except: pass
    log('Finished destroying spawned subprocesses.', 2)
