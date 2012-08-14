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
from multiprocessing import cpu_count
from collections import Counter
import os
import re
import socket

def broker_hostname(hosts):
    """Ensure broker hostname is routable, else return 127.0.0.1"""
    hostname = hosts[0][0]
    if hostname in localHostname() and len(hosts) > 1:
        hostname = socket.getfqdn().split(".")[0]
        try:
            socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            raise Exception("\nThe first host (broker) is not routable.\n"
                            "Make sure the address is correct.")
    return hostname

def localHostname():
    return ["127.0.0.1", socket.getfqdn().split('.')[0], "localhost"]

def getCPUcount():
    try:
        return cpu_count()
    except NotImplementedError:
        return 1


def getEnv():
    if "PBS_ENVIRONMENT" in os.environ:
        return "PBS"
    elif "PE_HOSTFILE" in os.environ:
        return "SGE"
    else:
        return "other"


def getHosts(filename=None, hostlist=None):
    if filename:
        return getHostsFromFile(filename)
    elif hostlist:
        return getHostsFromList(hostlist)
    elif "PBS_ENVIRONMENT" in os.environ:
        return getHostsFromPBS()
    elif "PE_HOSTFILE" in os.environ:
        return getHostsFromSGE()
    else:
        return getDefaultHosts()


def getHostsFromFile(filename):
    ValidHostname = r"[^ /\t=\n]*"  # TODO This won't work with ipv6 address
                                    # TODO find a better regex that works
                                    # with all valid hostnames
    workers = r"\d+"
    hn = re.compile(ValidHostname)
    w = re.compile(workers)
    hosts = []
    with open(filename) as f:
        for line in f:
            host = hn.search(line)
            if host:
                hostname = host.group()
                n = w.search(line[host.end():])
                if n:
                    n = n.group()
                else:
                    n = 1
                hosts.append((hostname, int(n)))
    return hosts


def getHostsFromList(hostlist):
    return [i for i in Counter(hostlist).items()]


def getHostsFromPBS():
    with open(os.environ["PBS_NODEFILE"], 'r') as hosts:
        return [i for i in Counter(hosts.read().split()).items()]


def getHostsFromSGE():
    with open(os.environ["PE_HOSTFILE"], 'r') as hosts:
        return [(host.split()[0], int(host.split()[1])) for host in hosts]


def getWorkerQte(hosts):
    if "PBS_NP" in os.environ:
        return int(os.environ["PBS_NP"])
    elif "NSLOTS" in os.environ:
        return int(os.environ["NSLOTS"])
    else:
        return sum(host[1] for host in hosts)


def KeyboardInterruptHandler(signum, frame):
    raise KeyboardInterrupt("Shutting down!")


def getDefaultHosts():
    return [('127.0.0.1', getCPUcount())]
