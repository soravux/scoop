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
        
def getHosts(filename = None, hostlist = None):
    if "PBS_ENVIRONMENT" in os.environ:
        return getHostsFromPBS()
    elif "PE_HOSTFILE" in os.environ:
        return getHostsFromSGE()
    else:
        if filename:
            return getHostsFromFile(filename)
        elif hostlist:
            return getHostsFromList(hostlist)

            
def getHostsFromFile(filename):
    """Parse the hostfile to get number of slots. The hostfile must have
    the following structure :
    hostname  slots=X
    hostname2 slots=X
    """
    with open(filename) as f:
        hosts = (line.split() for line in f)
        return [(h[0], int(h[1].split("=")[1])) for h in hosts]

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
        
        
