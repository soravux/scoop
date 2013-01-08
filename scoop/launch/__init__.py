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
# Global imports
from collections import namedtuple
import logging
import subprocess

# Local
from scoop import utils

baseSSH = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
launchingArguments = namedtuple(
    'launchingArguments',
    ['path', 'pythonPath', 'nice', 'workerNum', 'debug', 'profiling',
     'pythonExecutable', 'executable', 'args', 'brokerHostname',
     'brokerPorts', 'size',
     ]
)

class Host(object):
    def __init__(self, hostname="localhost"):
        self.workersArguments = []
        self.hostname = hostname
        self.subprocesses = []

    def __repr__(self):
        return "{0} ({1} workers)".format(
            self.hostname,
            len(self.workersArguments)
        )

    def isLocal(self):
        return self.hostname in utils.localHostnames

    def addWorker(self, path, pythonPath, nice, affinity, workerNum, debug,
             profiling, pythonExecutable, executable, args, brokerHostname,
             brokerPorts, size):
        #if self.isLocal():
        self.workersArguments.append(
            launchingArguments(path=path,
                               pythonPath=pythonPath,
                               nice=nice,
                               workerNum=workerNum,
                               debug=debug,
                               profiling=profiling,
                               pythonExecutable=pythonExecutable,
                               executable=executable,
                               args=args,
                               brokerHostname=brokerHostname,
                               brokerPorts=brokerPorts,
                               size=size,
                               )
        )


    def setCommand(self):
        # replace remoteSSHLaunch
        pass

    def getWorkerCommand(self, workerID=None):
        worker = self.workersArguments[workerID]
        pythonpath = ("export PYTHONPATH={0} "
                      "&&".format(worker.pythonPath) if worker.pythonPath else '')
        # If broker is on localhost
        if self.hostname == worker.brokerHostname:
            broker = "127.0.0.1"
        else:
            broker = worker.brokerHostname

        # If host is not localhost, echo group process
        if not self.isLocal() and workerID == 0:
            echoGroup = "--echoGroup "
        else:
            echoGroup = ''

        c = (
            "({pythonpath} cd {remotePath} && ("
            "{nice} {pythonExecutable} "
            "-m scoop.bootstrap.__main__ "
            "{echoGroup}"
            "--workerName {workersLeft} "
            "--brokerName broker "
            "--brokerAddress tcp://{brokerHostname}:{brokerPort} "
            "--metaAddress tcp://{brokerHostname}:{infoPort} "
            "--size {n} {origin}{debug}{profile}{executable} "
            "{arguments}))").format(
                remotePath=worker.path,
                pythonpath=pythonpath,
                nice='nice -n {0}'.format(worker.nice)
                if worker.nice is not None else '',
                origin='--origin ' if worker.workerNum == 1 else '',
                debug='--debug ' if worker.debug else '',
                profile='--profile ' if worker.profiling else '',
                pythonExecutable=worker.pythonExecutable,
                echoGroup=echoGroup,
                workersLeft=worker.workerNum,
                brokerHostname=broker,
                brokerPort=worker.brokerPorts[0],
                infoPort=worker.brokerPorts[1],
                n=worker.size,
                executable=worker.executable,
                arguments=" ".join(worker.args)
        )
        return c

    def getCommand(self):
        command = []
        for workerID, worker in enumerate(self.workersArguments):
            command.append(self.getWorkerCommand(workerID))
        return " & ".join(command)

    def launch(self, tunnelPorts=None, stdPipe=False):
        if self.isLocal():
            # Launching local workers
            for workerID, workerToLaunch in enumerate(self.workersArguments):
                # Launch one per subprocess
                c = self.getWorkerCommand(workerID)
                self.subprocesses.append(
                    subprocess.Popen(
                        c,
                        shell=True,
                        #stdin=subprocess.PIPE if stdPipe else None,
                        stdout=subprocess.PIPE if stdPipe else None,
                        stderr=subprocess.PIPE if stdPipe else None,
                    )
                )
        else:
            # Launching remotely
            sshCommand = baseSSH
            if tunnelPorts is not None:
                sshCommand += [
                    '-R {0}:127.0.0.1:{0}'.format(tunnelPorts[0]),
                    '-R {0}:127.0.0.1:{0}'.format(tunnelPorts[1]),
                ]
            self.subprocesses.append(
                subprocess.Popen(sshCommand
                                 + [self.hostname]
                                 + [self.getCommand()],
                                 #stdin=subprocess.PIPE if stdPipe else None,
                                 stdout=subprocess.PIPE if stdPipe else None,
                                 stderr=subprocess.PIPE if stdPipe else None,
                )
            )
        return self.subprocesses