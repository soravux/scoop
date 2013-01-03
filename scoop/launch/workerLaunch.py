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
import subprocess
from . import subprocessHandling


def localWorker(workerNum, size, pythonExecutable, executable, args,
                brokerAddress, infoAddress, debug, profiling):
    c = [pythonExecutable,
         "-m", "scoop.bootstrap.__main__",
         "--workerName", "worker{0}".format(workerNum),
         "--brokerName", "broker",
         "--brokerAddress",
         brokerAddress,
         "--metaAddress",
         infoAddress,
         "--size", str(size)]
    if workerNum == 1:
        c.append("--origin")
    if debug:
        logging.debug('Set debug on')
        c.append("--debug")
    if profiling:
        logging.info('Setting profiling on')
        c.append("--profile")
    c.append(executable)
    c.extend(args)
    logging.debug("localWorker: going to start %s" % c)
    return subprocess.Popen(c)

class remoteWorker(subprocessHandling.baseRemote):
    def __init__(self):
        self.command = []

    def addWorker(self, path, pythonPath, nice, workerNum, debug, profiling,
                 pythonExecutable, executable, args, brokerHostname,
                 brokerPorts, size, echoGroup=False, brokerIsLocalhost=False):
        pythonpath = ("export PYTHONPATH={0} "
                      "&&".format(pythonPath) if pythonPath else '')
        broker = "127.0.0.1" if brokerIsLocalhost else brokerHostname

        c = (
            "{pythonpath} cd {remotePath} && {nice} {pythonExecutable} "
            "-m scoop.bootstrap.__main__ "
            "{echoGroup}"
            "--workerName worker{workersLeft} "
            "--brokerName broker "
            "--brokerAddress tcp://{brokerHostname}:{brokerPort} "
            "--metaAddress tcp://{brokerHostname}:{infoPort} "
            "--size {n} {origin} {debug} {profile} {executable} "
            "{arguments}").format(
                remotePath=path,
                pythonpath=pythonPath,
                nice='nice -n {0}'.format(nice)
                if nice is not None else '',
                origin='--origin' if workerNum == 1 else '',
                debug='--debug' if debug else '',
                profile='--profile' if profiling else '',
                pythonExecutable=pythonExecutable,
                echoGroup='--echoGroup ' if echoGroup else '',
                workersLeft=workerNum,
                brokerHostname=brokerHostname,
                brokerPort=brokerPorts[0],
                infoPort=brokerPorts[1],
                n=size,
                executable=executable,
                arguments=" ".join(args)
        )
        logging.debug("addWorker: adding %s" % c)
        self.command.append(c)

    def getCommand(self):
        return self.command