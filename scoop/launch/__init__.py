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
import sys
import subprocess

# Local
from scoop import utils


class Host(object):
    """Represents an accessible computing resource.
       Can be remote (ssh via netowrk) or represent localhost."""
    BOOTSTRAP_MODULE = 'scoop.bootstrap.__main__'
    BASE_SSH = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
    LAUNCHING_ARGUMENTS = namedtuple(
        'launchingArguments',
        ['path', 'pythonPath', 'nice', 'workerNum', 'debug', 'profiling',
         'pythonExecutable', 'executable', 'args', 'brokerHostname',
         'brokerPorts', 'size',
         ]
    )

    def __init__(self, hostname="localhost"):
        self.workersArguments = []
        self.hostname = hostname
        self.subprocesses = []
        self.remoteProcessGID = None

    def __repr__(self):
        return "{0} ({1} workers)".format(
            self.hostname,
            len(self.workersArguments)
        )

    def isLocal(self):
        """Is the current host the localhost?"""
        return self.hostname in utils.localHostnames

    def addWorker(self, path, pythonPath, nice, affinity, workerNum, debug,
             profiling, pythonExecutable, executable, args, brokerHostname,
             brokerPorts, size):
        """Add a worker assignation"""
        self.workersArguments.append(
            self.LAUNCHING_ARGUMENTS(path=path,
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

    def _getWorkerCommandList(self, workerID):
        """Generate the workerCommand as list"""
        worker = self.workersArguments[workerID]

        c = ['(']
        if worker.pythonPath:
            # TODO: do we really want to set PYTHONPATH='' if not defined??
            c.extend(["export", "PYTHONPATH={0}:\$PYTHONPATH".format(worker.pythonPath), '&&'])

        c.extend(['cd', worker.path, '&&'])
        c.append('(')

        if worker.nice is not None:
            c.extend(['nice', '-n', str(worker.nice)])

        c.extend([worker.pythonExecutable, '-m', self.BOOTSTRAP_MODULE])

        # If broker is on localhost
        if self.hostname == worker.brokerHostname:
            broker = "127.0.0.1"
        else:
            broker = worker.brokerHostname
        # If host is not localhost, echo group process
        if not self.isLocal() and workerID == 0:
            c.append("--echoGroup ")

        c.extend(['--workerName', str(worker.workerNum)])

        c.extend(['--brokerName', 'broker'])
        c.extend(['--brokerAddress',
                  'tcp://{brokerHostname}:{brokerPort}'.format(brokerHostname=broker,
                                                               brokerPort=worker.brokerPorts[0])
                  ])
        c.extend(['--metaAddress',
                  'tcp://{brokerHostname}:{infoPort}'.format(brokerHostname=broker,
                                                             infoPort=worker.brokerPorts[1])
                  ])
        c.extend(['--size', str(worker.size)])
        if worker.workerNum == 1:
            c.append('--origin')
        if worker.debug:
            c.append('--debug')
        if worker.profiling:
            c.append('--profile')

        c.append(worker.executable)
        # This trick is used to parse correctly quotes (ie. myScript.py 'arg1 "arg2" arg3')
        # Because shell=True is set with Popen, every quote gets re-interpreted
        # It replaces simple quotation marks with \\\" which gets evaluated to \" by
        # the second shell which prints it out as a double quote.
        c.extend(['"{0}"'.format(a.replace('"', '\\\"')) for a in worker.args])

        c.append(')')  # closes nice
        c.append(')')  # closes initial

        return c

    def getWorkerCommand(self, workerID=None):
        """Retrieves the working launching shell command."""
        c = (" ".join(self._getWorkerCommandList(workerID)))
        return c

    def getCommand(self):
        """Retrieves the shell command to launch every worker on this host."""
        command = []
        for workerID, worker in enumerate(self.workersArguments):
            command.append(self.getWorkerCommand(workerID))
        return " & ".join(command)

    def launch(self, tunnelPorts=None, stdPipe=False):
        """Launch every worker assigned on this host."""
        if self.isLocal():
            # Launching local workers
            for workerID, workerToLaunch in enumerate(self.workersArguments):
                # Launch one per subprocess
                c = self.getWorkerCommand(workerID)
                self.subprocesses.append(
                    subprocess.Popen(
                        c,
                        shell=True,
                        # stdin=subprocess.PIPE if stdPipe else None,
                        stdout=subprocess.PIPE if stdPipe else None,
                        stderr=subprocess.PIPE if stdPipe else None,
                    )
                )
        else:
            # Launching remotely
            sshCommand = self.BASE_SSH
            if tunnelPorts is not None:
                sshCommand += [
                    '-R {0}:127.0.0.1:{0}'.format(tunnelPorts[0]),
                    '-R {0}:127.0.0.1:{0}'.format(tunnelPorts[1]),
                ]
            self.subprocesses.append(
                subprocess.Popen(sshCommand
                                 + [self.hostname]
                                 + [self.getCommand()],
                                 # stdin=subprocess.PIPE if stdPipe else None,
                                 stdout=subprocess.PIPE if stdPipe else None,
                                 stderr=subprocess.PIPE if stdPipe else None,
                )
            )
            # Get group id from remote connections
            try:
                self.remoteProcessGID = int(
                    self.subprocesses[-1].stdout.readline().strip()
                )
            except ValueError:
                logging.info("Could not get process information for host "
                             "{0}.".format(
                                self.createdRemoteConn[thisRemote][0],
                                )
                             )
        return self.subprocesses

    def close(self):
        """Connection(s) cleanup."""
        # Ensure everything is cleaned up on exit

        logging.debug('Closing workers on {0}.'.format(self))

        # Terminate subprocesses
        for process in self.subprocesses:
            try:
                process.terminate()
            except OSError:
                pass

        # Send termination signal to remaining workers
        if not self.isLocal() and self.remoteProcessGID is None:
                logging.info("Zombie process(es) possibly left on "
                             "host {0}!".format(self.hostname))
        elif not self.isLocal():
            command = "kill -9 -{0} &>/dev/null".format(self.remoteProcessGID)
            subprocess.Popen(self.BASE_SSH
                             + [self.hostname]
                             + [command],
                             shell=True,
            ).wait()

        for process in self.subprocesses:
            if process.stdout is not None:
                sys.stdout.write(process.stdout.read().decode("utf-8"))
                sys.stdout.flush()

            if process.stderr is not None:
                sys.stderr.write(process.stderr.read().decode("utf-8"))
                sys.stderr.flush()