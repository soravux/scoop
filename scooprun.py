#!/usr/bin/env python
from __future__ import print_function
import subprocess
import argparse
import time
import os
import socket

def log(text, level=0):
    """Easily logs on screen the different events happening based on the
    verbosity level"""
    if args.verbose > level-1:
        print("[{0}]\tscooprun -> {1}".format(time.time(), text))

cwd = os.getcwd()
    
parser = argparse.ArgumentParser(description='Starts the executable on the nodes.',
                                 fromfile_prefix_chars='@')
parser.add_argument('--hosts', '--host',
                    help='A file containing a list of hosts',
                    nargs='*')
parser.add_argument('--path', '-p',
                    help="The path to the executable on remote hosts",
                    default=cwd)
parser.add_argument('--nice',
                    type=int,
                    help="Nice level")
parser.add_argument('--verbose', '-v',
                    action='count',
                    help="Verbosity level")
parser.add_argument('-N',
                    help="Number of process",
                    type=int,
                    default=2)
parser.add_argument('-b',
                    help="Don't start additional workers on the local machine, only the broker and the origin",
                    action='store_true')
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
                    default=["python"])
args = parser.parse_args()

hosts = [] if args.hosts == None else args.hosts
hosts += ['127.0.0.1'] if not args.b else []
hosts = set(hosts)
workers_left = args.N - 1 # One is the origin, already taken into account
created_subprocesses = []

log('Deploying {0} workers over {1} host(s).'.format(args.N, len(hosts)), 2)

# Division of workers pseudo-equally upon the hosts
maximum_workers = {}
for index, host in enumerate(hosts):
    maximum_workers[host] = (args.N / (len(hosts)) + int((args.N % len(hosts)) > index))

if args.broker_hostname == None:
    broker_hostname = socket.gethostname()
else:
    broker_hostname = args.broker_hostname[0]
log('Using hostname/ip: "{0}" as external broker reference.'.format(broker_hostname), 1)

try:
    # Launching the local broker
    log('Initialising local broker.', 1)
    created_subprocesses.append(subprocess.Popen([args.python_executable[0], 'broker.py']))
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
            
    for index, host in enumerate(hosts):
        if host in ["127.0.0.1", "localhost"]:
            # Launching the workers
            log('Initialising local workers attached to the local broker...', 1)
            for n in range(min(maximum_workers['127.0.0.1'], workers_left)):
                log('Initialising local worker {0}.'.format(n), 2)
                os.environ.update({'WORKER_NAME': 'worker{0}'.format(n),
                                   'IS_ORIGIN': '0'})
                created_subprocesses.append(subprocess.Popen([args.python_executable[0]] \
                    + args.executable))
                workers_left -= 1
        else:
            # If the host is remote, connect with ssh
            log('Initialising remote workers of host {0} attached to the local broker...'.format(host), 1)
            for a in range(min(maximum_workers.get(host, 8), workers_left)):
                log('Initialising remote worker {0}'.format(workers_left), 2)
                command = 'PYTHONPATH={5} \
IS_ORIGIN=0 \
WORKER_NAME=worker{3} \
BROKER_NAME=broker \
BROKER_ADDRESS=tcp://{2}:5555 \
META_ADDRESS=tcp://{2}:5556 {4} {0} {1}'.format(
                    os.path.join(args.path + "/", args.executable[0]),
                    " ".join(args.executable[1:]),
                    '127.0.0.1' if args.e else broker_hostname,
                    workers_left,
                    args.python_executable[0],
                    os.environ.get("PYTHONPATH", "$PYTHONPATH"))
                # TODO: start every worker in one SSH channel.
                ssh_command = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
                if args.e:
                    ssh_command += ['-R 5555:127.0.0.1:5555', '-R 5556:127.0.0.1:5556']
                shell = subprocess.Popen(ssh_command + [host,
                                                        command])
                created_subprocesses.append(shell)
                workers_left -= 1
        if workers_left <= 0: break
    # Everything has been started everywhere, we can then launch our origin.
    log('Initialising local origin.', 1)
    os.environ.update({'WORKER_NAME': 'root',
                       'IS_ORIGIN': '1'})
    created_subprocesses.append(subprocess.call([args.python_executable[0]] + args.executable))
finally:
    # Ensure everything is cleaned up on exit
    log('Destroying local elements of the federation...', 1)
    for process in created_subprocesses:
        try: process.terminate()
        except: pass
    log('Finished destroying spawned subprocesses.', 2)
