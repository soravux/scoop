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
from threading import Thread
import subprocess
import shlex
import sys
import os
try:
    import cPickle as pickle
except ImportError:
    import pickle

import scoop
from .constants import BASE_SSH, BASE_RSH
try:
    import psutil
except ImportError:
    psutil = None


class localBroker(object):
    def __init__(self, debug, nice=0, backend='ZMQ'):
        """Starts a broker on random unoccupied ports"""
        self.backend = backend
        if backend == 'ZMQ':
            from ..broker.brokerzmq import Broker
        else:
            from ..broker.brokertcp import Broker
        if nice:
            if not psutil:
                scoop.logger.error("'nice' used while psutil not installed.")
                raise ImportError("psutil is needed for nice functionnality.")
            p = psutil.Process(os.getpid())
            p.set_nice(nice)
        self.localBroker = Broker(debug=debug)
        self.brokerPort, self.infoPort = self.localBroker.getPorts()
        self.broker = Thread(target=self.localBroker.run)
        self.broker.daemon = True
        self.broker.start()
        scoop.logger.debug("Local broker launched on ports {0}, {1}"
                      ".".format(self.brokerPort, self.infoPort))

    def sendConnect(self, data):
        """Send a CONNECT command to the broker
            :param data: List of other broker main socket URL"""
        # Imported dynamically - Not used if only one broker
        if self.backend == 'ZMQ':
            import zmq
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.DEALER)
            self.socket.setsockopt(zmq.IDENTITY, b'launcher')
            self.socket.connect(
                "tcp://127.0.0.1:{port}".format(
                    port=self.brokerPort,
                )
            )
            self.socket.send_multipart([b"CONNECT",
                                        pickle.dumps(data,
                                                     pickle.HIGHEST_PROTOCOL)])
        else:
            # TODO
            pass

    def getHost(self):
        return "127.0.0.1"

    def getPorts(self):
        return (self.brokerPort, self.infoPort)

    def close(self):
        scoop.logger.debug('Closing local broker.')


class remoteBroker(object):
    def __init__(self, hostname, pythonExecutable, debug=False, nice=0,
                 backend='ZMQ', rsh=False, ssh_executable='ssh'):
        """Starts a broker on the specified hostname on unoccupied ports"""
        self.backend = backend
        brokerString = ("{pythonExec} -m scoop.broker.__main__ "
                        "--echoGroup "
                        "--echoPorts "
                        "--backend {backend} ".format(
                            pythonExec=pythonExecutable,
                            backend=backend,
                            )
                        )
        if nice:
            brokerString += "--nice {nice} ".format(nice=nice)
        if debug:
            brokerString += "--debug --path {path} ".format(
                path=os.getcwd()
            )
        self.hostname = hostname

        BASE_SSH[0] = ssh_executable
        cmd = BASE_RSH if rsh else BASE_SSH + [
            hostname,
            brokerString.format(pythonExec=pythonExecutable)
        ]

        scoop.logger.debug("Launching remote broker: {cmd}"
                           "".format(cmd=" ".join(cmd)))
        self.shell = subprocess.Popen(
            cmd,
            bufsize=0,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Get remote process group ID
        try:
            self.remoteProcessGID = int(self.shell.stdout.readline().strip())
        except ValueError:
            self.remoteProcessGID = None

        # Get remote ports
        receivedLine = self.shell.stdout.readline()
        try:
            ports = receivedLine.decode().strip().split(",")
            self.brokerPort, self.infoPort = ports
        except ValueError:
            # Following line for Python 2.6 compatibility (instead of [as e])
            e = sys.exc_info()[1]

            # Terminate the process, otherwide reading from stderr may wait
            # undefinitely
            self.shell.terminate()

            stderr = self.shell.stderr.read()
            raise Exception("Could not successfully launch the remote broker.\n"
                            "Requested remote broker ports, received:\n"
                            "{receivedLine}\n"
                            "Port number decoding error:\n{e}\n"
                            "SSH process stderr:\n{stderr}".format(**locals()))

        scoop.logger.debug("Foreign broker launched on ports {0}, {1} of host {2}"
                      ".".format(self.brokerPort,
                                 self.infoPort,
                                 hostname,
                                 )
                      )

    def sendConnect(self, data):
        """Send a CONNECT command to the broker
            :param data: List of other broker main socket URL"""
        # Imported dynamically - Not used if only one broker
        if self.backend == 'ZMQ':
            import zmq
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.DEALER)
            if sys.version_info < (3,):
                self.socket.setsockopt_string(zmq.IDENTITY, unicode('launcher'))
            else:
                self.socket.setsockopt_string(zmq.IDENTITY, 'launcher')
            self.socket.connect(
                "tcp://{hostname}:{port}".format(
                    port=self.brokerPort,
                    hostname = self.hostname
                )
            )
            self.socket.send_multipart([b"CONNECT",
                                        pickle.dumps(data,
                                                     pickle.HIGHEST_PROTOCOL)])
        else:
            # TODO
            pass


    def getHost(self):
        return self.hostname

    def getPorts(self):
        return (self.brokerPort, self.infoPort)

    def isLocal(self):
        """Is the current broker on the localhost?"""
        # This exists for further fusion with localBroker
        return False
        # return self.hostname in utils.localHostnames

    def close(self):
        """Connection(s) cleanup."""
        # TODO: DRY with workerLaunch.py
        # Ensure everything is cleaned up on exit
        scoop.logger.debug('Closing broker on host {0}.'.format(self.hostname))

        # Terminate subprocesses
        try:
            self.shell.terminate()
        except OSError:
            pass

        # Output child processes stdout and stderr to console
        sys.stdout.write(self.shell.stdout.read().decode("utf-8"))
        sys.stdout.flush()

        sys.stderr.write(self.shell.stderr.read().decode("utf-8"))
        sys.stderr.flush()
