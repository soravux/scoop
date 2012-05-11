#!/usr/bin/env python
from __future__ import print_function
import subprocess
import argparse
import time
import os
import socket

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
                    type=int)
parser.add_argument('executable',
                    nargs='+',
                    help='The executable to start with scoop and its arguments')
args = parser.parse_args()

hosts = [] if args.hosts == None else args.hosts
hosts += ['127.0.0.1'] # Ensure local machine is in the list
created_subprocesses = []

workers_left = args.N
maximum_workers = {'127.0.0.1': 32,}

# Remove link-local and loopback (see RFC 5735 and RFC 3330)
broker_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.") and not ip.startswith("169.254.")][0]
if args.verbose > 0: print("[{0}]\tscooprun -> Using IPv4 {1} address for broker.".format(time.time(), broker_ip))

try:
    for index, host in enumerate(hosts):
        if host in ["127.0.0.1", "localhost"]:
            if args.verbose > 0: print("[{0}]\tscooprun -> Initialising local \
element of the federation.".format(time.time()))
            # Launching the broker
            if args.verbose > 1: print("[{0}]\tscooprun -> Initialising local \
broker.".format(time.time()))
            created_subprocesses.append(subprocess.Popen(['python', 'broker.py']))
            time.sleep(1) # Get something better than this?
            
            # Launching the workers
            for n in range(min(maximum_workers['127.0.0.1'], workers_left) + 1):
                if args.verbose > 1: print("[{0}]\tscooprun -> Initialising local \
worker.".format(time.time()))
                os.environ.update({'WORKER_NAME': 'worker{0}'.format(n),
                                   'IS_ORIGIN': '0'})
                created_subprocesses.append(subprocess.Popen(['python'] \
                    + args.executable))
                workers_left -= 1
        else:
            if args.verbose > 0: print("[{0}]\tscooprun -> Initialising remote \
element of the federation <{1}>.".format(time.time(), host))
            # If the host is remote, connect with ssh
            shell = subprocess.Popen(['ssh', '-x', '-n', host,
                                      'IS_ORIGIN=0 WORKER_NAME={3} BROKER_NAME=broker BROKER_ADDRESS=tcp://{2}:5555 META_ADDRESS=tcp://{2}:5556 python {0} {1}'.format(
                                        os.path.join(args.path, args.executable[0]),
                                        " ".join(args.executable[1:]),
                                        broker_ip,
                                        workers_left)])
            workers_left -= 1
    # Everything has been started everywhere, we can then launch our origin.
    # TODO: the origin could be anywhere else
    if args.verbose > 1: print("[{0}]\tscooprun -> Initialising local \
origin.".format(time.time()))
    os.environ.update({'WORKER_NAME': 'root',
                       'IS_ORIGIN': '1'})
    created_subprocesses.append(subprocess.call(['python'] + args.executable))
finally:
    # Ensure everything is cleaned up on exit
    if args.verbose > 0: print("[{0}]\tscooprun -> Destroying local \
element of the federation.".format(time.time()))
    for process in created_subprocesses:
        try: process.kill()
        except: pass
    if args.verbose > 0: print("[{0}]\tscooprun -> Destroyed subprocesses."\
        .format(time.time()))