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
from itertools import groupby
import os
import re
import sys
import socket
import logging

if sys.version_info < (2, 7):
    from scoop.backports.dictconfig import dictConfig
else:
    from logging.config import dictConfig


loopbackReferences = [
    "127.0.0.1",
    "localhost",
    "::1",
]

localHostnames = loopbackReferences + [
    socket.getfqdn().split('.')[0],
]

localHostnames.extend([
    ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
        if not ip.startswith("127.")][:1]
)


def initLogging(default_verbosity=0, log=None):
        """Creates a logger.
        dictConfig is used to limit interference with user loggers. basicConfig
        would override user code."""
        verbose_levels = {
            -2: "CRITICAL",
            -1: "ERROR",
            0: "WARNING",
            1: "INFO",
            2: "DEBUG",
            3: "NOSET",
        }
        log_handlers = {
            "console":
            {
                "class": "logging.StreamHandler",
                "formatter": "SCOOPFormatter",
                "stream": "ext://sys.stdout",
            },
        }
        dict_log_config = {
            "version": 1,
            "handlers": log_handlers,
            "loggers":
            {
                "SCOOPLogger":
                {
                    "handlers": ["console"],
                    "level": verbose_levels[default_verbosity],
                },
            },
            "formatters":
            {
                "SCOOPFormatter":
                {
                    "format": "[%(asctime)-15s] %(module)-9s (unconnected) "
                              "%(levelname)-7s %(message)s",
                },
            },
        }
        dictConfig(dict_log_config)
        return logging.getLogger("SCOOPLogger")


def externalHostname(hosts):
    """Ensure external hostname is routable."""
    hostname = hosts[0][0]
    if hostname in localHostnames and len(hosts) > 1:
        hostname = socket.getfqdn().split(".")[0]
        try:
            socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            raise Exception("\nThe first host (containing a broker) is not"
                            " routable.\nMake sure the address is correct.")
    return hostname


def groupTogether(in_list):
    # TODO: This algorithm is not efficient, use itertools.groupby()
    return_value = []
    already_done = []
    for index, element in enumerate(in_list):
        if element not in already_done:
            how_much = in_list[index + 1:].count(element)
            return_value += [element]*(how_much + 1)
            already_done.append(element)
    return return_value


def getCPUcount():
    """Try to get the number of cpu on the current host."""
    try:
        return cpu_count()
    except NotImplementedError:
        return 1


def getEnv():
    """Return the launching environnement"""
    if "PBS_ENVIRONMENT" in os.environ:
        return "PBS"
    elif "PE_HOSTFILE" in os.environ:
        return "SGE"
    else:
        return "other"


def getHosts(filename=None, hostlist=None):
    """Return a list of host depending on the environment"""
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
    """Parse a file to return a list of hosts."""
    valid_hostname = r"^[^ /\t=\n]+"
    workers = r"\d+"
    hostname_re = re.compile(valid_hostname)
    worker_re = re.compile(workers)
    hosts = []
    with open(filename) as f:
        for line in f:
            host = hostname_re.search(line.strip())
            if host:
                hostname = host.group()
                n = worker_re.search(line[host.end():])
                if n:
                    n = n.group()
                else:
                    n = 1
                hosts.append((hostname, int(n)))
    return hosts


def getHostsFromList(hostlist):
    """Return the hosts from the command line"""
    # Counter would be more efficient but:
    # 1. Won't be Python 2.6 compatible
    # 2. Won't be ordered
    hostlist = groupTogether(hostlist)
    retVal = []
    for key, group in groupby(hostlist):
        retVal.append((key, len(list(group))))
    return retVal


def getHostsFromPBS():
    """Return a host list in a PBS environment"""
    # See above comment about Counter
    with open(os.environ["PBS_NODEFILE"], 'r') as hosts:
        hostlist = groupTogether(hosts.read().split())
        retVal = []
        for key, group in groupby(hostlist):
            retVal.append((key, len(list(group))))
        return retVal


def getHostsFromSGE():
    """Return a host list in a SGE environment"""
    with open(os.environ["PE_HOSTFILE"], 'r') as hosts:
        return [(host.split()[0], int(host.split()[1])) for host in hosts]


def getWorkerQte(hosts):
    """Return the number of workers to launch depending on the environment"""
    if "PBS_NP" in os.environ:
        return int(os.environ["PBS_NP"])
    elif "NSLOTS" in os.environ:
        return int(os.environ["NSLOTS"])
    else:
        return sum(host[1] for host in hosts)


def KeyboardInterruptHandler(signum, frame):
    """This is use in the interruption handler"""
    raise KeyboardInterrupt("Shutting down!")


def getDefaultHosts():
    """This is the default host for a simple SCOOP launch"""
    return [('127.0.0.1', getCPUcount())]


try:
    # Python 2.X  fallback
    basestring  # attempt to evaluate basestring
    def isStr(string):
        return isinstance(string, basestring)
except NameError:
    def isStr(string):
        return isinstance(string, str)
