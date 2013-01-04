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
import logging

from . import subprocessHandling


def localWorker(nice, workerNum, size, pythonExecutable, executable, args,
                brokerAddress, infoAddress, debug, profiling):
    c = []
    if nice is not None:
        c.extend(['nice', '-n', '{0}'.format(nice)])
    c.extend([
         pythonExecutable,
         "-m", "scoop.bootstrap.__main__",
         "--workerName", str(workerNum),
         "--brokerName", "broker",
         "--brokerAddress",
         brokerAddress,
         "--metaAddress",
         infoAddress,
         "--size", str(size)
         ])
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
    logging.debug("Launching locally '{0}'".format(" ".join(c)))
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
            "{nice} {pythonExecutable} "
            "-m scoop.bootstrap.__main__ "
            "{echoGroup}"
            "--workerName {workersLeft} "
            "--brokerName broker "
            "--brokerAddress tcp://{brokerHostname}:{brokerPort} "
            "--metaAddress tcp://{brokerHostname}:{infoPort} "
            "--size {n} {origin} {debug} {profile} {executable} "
            "{arguments}").format(
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
        if len(self.command) == 0:
            # If it is the first worker on the host, change directory
            self.command.append("{pythonpath} cd {remotePath} && (".format(
                remotePath=path,
                pythonpath=pythonPath,
            ))
        else:
            # If not the first, add an amperstand for background execution
            self.command.append("&")
        self.command.append(c)

    def getCommand(self):
        if self.command:
            return self.command + [")"]
        return []