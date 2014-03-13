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
import scoop
from scoop import utils


class Host(object):
    """Represents an accessible computing resource.
       Can be remote (ssh via netowrk) or represent localhost."""
    BOOTSTRAP_MODULE = 'scoop.bootstrap.__main__'
    BASE_SSH = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']
    LAUNCHING_ARGUMENTS = namedtuple(
        'launchingArguments',
        [
            'pythonPath', 'path', 'nice', 'pythonExecutable', 'size', 'origin',
            'brokerHostname', 'brokerPorts', 'debug', 'profiling', 'executable',
            'verbose', 'args', 'prolog', 'backend'
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

    def addWorker(self, *args, **kwargs):
        """Add a worker assignation
            arguments and order to pass are defined in LAUNCHING_ARGUMENTS
            Using named args is advised.
        """
        try:
            la = self.LAUNCHING_ARGUMENTS(*args, **kwargs)
        except TypeError as e:
            scoop.logger.error(("addWorker failed to convert args %s and kwargs %s "
                            "to namedtuple (requires %s arguments (names %s)") %
                            (args, kwargs, len(self.LAUNCHING_ARGUMENTS._fields),
                             self.LAUNCHING_ARGUMENTS._fields))

        self.workersArguments.append(la)

    def _WorkerCommand_environment(self, worker):
        """Return list of shell commands to prepare the environment for bootstrap"""
        c = []
        if worker.prolog:
            c.extend([
                "source",
                worker.prolog,
                "&&",
            ])
        if worker.pythonPath:
            # Tried to make it compliant to all shell variants.
            c.extend([
                "export",
                "PYTHONPATH={0}:$PYTHONPATH".format(worker.pythonPath),
                ">&/dev/null",
                "||",
                "setenv",
                "PYTHONPATH",
                "{0}:$PYTHONPATH".format(worker.pythonPath),
                "&&",
            ])
        return c

    def _WorkerCommand_bootstrap(self, worker):
        """Return list commands to start the bootstrap process"""
        c = []
        c.extend([worker.pythonExecutable, '-m', self.BOOTSTRAP_MODULE])
        return c

    def _WorkerCommand_options(self, worker, workerID):
        """Return list of options for bootstrap"""
        c = []
        # If broker is on localhost
        if self.hostname == worker.brokerHostname:
            broker = "127.0.0.1"
        else:
            broker = worker.brokerHostname

        # If host is not localhost, echo group process
        if not self.isLocal() and workerID == 0:
            c.append("--echoGroup ")

        if worker.nice is not None:
            c.extend(['--nice', str(worker.nice)])
        c.extend(['--size', str(worker.size)])
        c.extend(['--workingDirectory', str(worker.path)])
        c.extend(['--brokerHostname', broker])
        c.extend(['--externalBrokerHostname', worker.brokerHostname])
        c.extend(['--taskPort', str(worker.brokerPorts[0])])
        c.extend(['--metaPort', str(worker.brokerPorts[1])])
        if worker.origin and worker.executable:
            c.append('--origin')
        if worker.debug:
            c.append('--debug')
        if worker.profiling:
            c.append('--profile')
        if worker.backend:
            c.append('--backend={0}'.format(worker.backend))
        if worker.verbose == 0:
            c.append('-q')
        elif worker.verbose >= 2:
            c.append('-v')
        return c

    def _WorkerCommand_executable(self, worker):
        """Return executable and any options to be executed by bootstrap"""
        c = []
        if worker.executable:
            c.append(worker.executable)
        # This trick is used to parse correctly quotes
        # (ie. myScript.py 'arg1 "arg2" arg3')
        # Because shell=True is set with Popen, every quote gets re-interpreted
        # It replaces simple quotation marks with \\\" which gets evaluated to
        # \" by the second shell which prints it out as a double quote.
        if worker.args:
            if self.isLocal():
                # If local, no shell is used so no escaping needed
                c.extend([
                    '{0}'.format(a) for a in worker.args
                ])
            else:
                c.extend([
                    '"{0}"'.format(a.replace('"', '\\\"')) for a in worker.args
                ])
        return c

    def _getWorkerCommandList(self, workerID):
        """Generate the workerCommand as list"""
        worker = self.workersArguments[workerID]

        c = []
        if not self.isLocal():
            c.extend(self._WorkerCommand_environment(worker))

        c.extend(self._WorkerCommand_bootstrap(worker))
        c.extend(self._WorkerCommand_options(worker, workerID))
        c.extend(self._WorkerCommand_executable(worker))

        return c

    def getWorkerCommand(self, workerID=None):
        """Retrieves the working launching shell command."""
        c = " ".join(self._getWorkerCommandList(workerID))
        return c

    def getCommand(self):
        """Retrieves the shell command to launch every worker on this host."""
        # All this parenthesis insanity is to start subshells (workers) in the
        # correct monitoring mode (no background job echo).
        # Output: ( [launch command 1] & ) && ( [launch command 2] & ) [...]
        command = []
        for workerID, worker in enumerate(self.workersArguments):
            command.append("(" + self.getWorkerCommand(workerID))
        command[-1] += ")"
        return " & ) && ".join(command)

    def launch(self, tunnelPorts=None, stdPipe=False):
        """Launch every worker assigned on this host."""
        if self.isLocal():
            # Launching local workers
            for workerID, workerToLaunch in enumerate(self.workersArguments):
                # Launch one per subprocess
                c = self._getWorkerCommandList(workerID)
                self.subprocesses.append(
                    subprocess.Popen(c)
                )
        else:
            # Launching remotely
            sshCmd = self.BASE_SSH
            if tunnelPorts is not None:
                sshCmd += [
                    '-R {0}:127.0.0.1:{0}'.format(tunnelPorts[0]),
                    '-R {0}:127.0.0.1:{0}'.format(tunnelPorts[1]),
                ]
            self.subprocesses.append(
                subprocess.Popen(sshCmd + [self.hostname, self.getCommand()],
                                 stdout=subprocess.PIPE if stdPipe else None,
                                 stderr=subprocess.PIPE if stdPipe else None,
                )
            )
            # Get group id from remote connections
            receivedLine = self.subprocesses[-1].stdout.readline()
            try:
                textGID = receivedLine.decode().strip()
                self.remoteProcessGID = int(textGID)
            except ValueError:
                # Following line for Python 2.6 compatibility (instead of [as e])
                e = sys.exc_info()[1]

                # Terminate the process, otherwide reading from stderr may wait
                # undefinitely
                self.subprocesses[-1].terminate()

                stderr = self.subprocesses[-1].stderr.read()
                hostname = self.hostname
                scoop.logger.warning("Could not successfully launch the remote "
                                 "worker on {hostname}.\n"
                                 "Requested remote group process id, "
                                 "received:\n{receivedLine}\n"
                                 "Group id decoding error:\n{e}\n"
                                 "SSH process stderr:\n{stderr}"
                                 "".format(**locals()))

        return self.subprocesses

    def close(self):
        """Connection(s) cleanup."""
        # Ensure everything is cleaned up on exit
        scoop.logger.debug('Closing workers on {0}.'.format(self))

        # Output child processes stdout and stderr to console
        for process in self.subprocesses:
            if process.stdout is not None:
                sys.stdout.write(process.stdout.read().decode("utf-8"))
                sys.stdout.flush()

            if process.stderr is not None:
                sys.stderr.write(process.stderr.read().decode("utf-8"))
                sys.stderr.flush()

        # Terminate subprocesses
        for process in self.subprocesses:
            try:
                process.terminate()
            except OSError:
                pass

        # Send termination signal to remaining workers
        if not self.isLocal() and self.remoteProcessGID is None:
                scoop.logger.warn("Zombie process(es) possibly left on "
                             "host {0}!".format(self.hostname))
        elif not self.isLocal():
            command = ("python -c "
                       "'import os, signal; os.killpg({0}, signal.SIGKILL)' "
                       ">&/dev/null").format(self.remoteProcessGID)
            subprocess.Popen(self.BASE_SSH
                             + [self.hostname]
                             + [command],
            ).wait()
