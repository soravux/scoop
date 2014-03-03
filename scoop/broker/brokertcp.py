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
from collections import deque, defaultdict
import time
import sys
import threading
import array
import socket
import copy
import asyncore
import logging
try:
    import cPickle as pickle
except ImportError:
    import pickle

import scoop
from .. import discovery, utils
from .structs import BrokerInfo

# Worker requests
INIT = b"INIT"
REQUEST = b"REQUEST"
TASK = b"TASK"
REPLY = b"REPLY"
SHUTDOWN = b"SHUTDOWN"
VARIABLE = b"VARIABLE"
BROKER_INFO = b"BROKER_INFO"
# Broker interconnection
CONNECT = b"CONNECT"


class LaunchingError(Exception): pass


def serialize(*data):
    #sendData = ''.join(data)
    #sendData = _chr(len(sendData)) + sendData
    #return array.array('b', sendData).tobytes()
    return pickle.dumps(data)

def deserialize(data):
    #return array.frombytes(data)
    return pickle.loads(data)


class TaskHandler(asyncore.dispatcher_with_send):
    def handle_read(self):
        data = self.recv(8192)
        if data:
            msg = deserialize(data)
        msg_type = msg[1]

        if self.debug:
            self.stats.append((time.time(),
                               msg_type,
                               len(self.unassignedTasks),
                               len(self.availableWorkers)))

        # New task inbound
        if msg_type in TASK:
            task = msg[2]
            try:
                address = self.availableWorkers.popleft()
            except IndexError:
                self.unassignedTasks.append(task)
            else:
                self.taskSocket.send_multipart([address, TASK, task])

        # Request for task
        elif msg_type == REQUEST:
            address = msg[0]
            try:
                task = self.unassignedTasks.pop()
            except IndexError:
                self.availableWorkers.append(address)
            else:
                self.taskSocket.send_multipart([address, TASK, task])

        # Answer needing delivery
        elif msg_type == REPLY:
            destination = msg[-1]
            origin = msg[0]
            self.taskSocket.send_multipart([destination] + msg[1:] + [origin])

        # Shared variable to distribute
        elif msg_type == VARIABLE:
            address = msg[4]
            value = msg[3]
            key = msg[2]
            self.sharedVariables[address].update(
                {key: value},
            )
            self.infoSocket.send_multipart([VARIABLE,
                                            key,
                                            value,
                                            address])

        # Initialize the variables of a new worker
        elif msg_type == INIT:
            address = msg[0]
            try:
                self.processConfig(pickle.loads(msg[2]))
            except pickle.PickleError:
                return
            self.taskSocket.send_multipart([
                address,
                pickle.dumps(self.config,
                             pickle.HIGHEST_PROTOCOL),
                pickle.dumps(self.sharedVariables,
                             pickle.HIGHEST_PROTOCOL),
            ])

            self.taskSocket.send_multipart([
                address,
                pickle.dumps(self.clusterAvailable,
                             pickle.HIGHEST_PROTOCOL),
            ])

        # Add a given broker to its fellow list
        elif msg_type == CONNECT:
            try:
                connect_brokers = pickle.loads(msg[2])
            except pickle.PickleError:
                self.logger.error("Could not understand CONNECT message.")
                return
            self.logger.info("Connecting to other brokers...")
            self.addBrokerList(connect_brokers)

        # Shutdown of this broker was requested
        elif msg_type == SHUTDOWN:
            self.logger.debug("SHUTDOWN command received.")
            raise asyncore.ExitNow('Server is quitting!')


class TaskServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(1)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print('Incoming connection from %s' % repr(addr))
            handler = TaskHandler(sock)


class InfoServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(1)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print('Incoming connection from %s' % repr(addr))
            handler = TaskHandler(sock)


class Broker(object):
    def __init__(self, tSock="tcp://*:*", mSock="tcp://*:*", debug=False,
                 headless=False, hostname="127.0.0.1"):
        """This function initializes a broker.

        :param tSock: Task Socket Address.
        Must contain protocol, address  and port information.
        :param mSock: Meta Socket Address.
        Must contain protocol, address and port information.
        """
        self.debug = debug
        self.hostname = hostname

        self.tSockPort = 0
        addr, port = tSock[6:].split(":", 1)
        if port == "*":
            port = 0
        else:
            port = int(port)
        if addr == "*":
            addr = ""
        self.taskSocket = TaskServer(addr, port)
        self.tSockPort = self.taskSocket.socket.getsockname()[1]

        # Create identifier for this broker
        self.name = "{0}:{1}".format(hostname, self.tSockPort)

        # Initialize broker logging
        self.logger = utils.initLogging(2 if debug else 0)
        self.logger.handlers[0].setFormatter(
            logging.Formatter(
                "[%(asctime)-15s] %(module)-9s ({0}) %(levelname)-7s "
                "%(message)s".format(self.name)
            )
        )

        self.infoSockPort = 0
        addr, port = mSock[6:].split(":", 1)
        if port == "*":
            port = 0
        else:
            port = int(port)
        if addr == "*":
            addr = ""
        self.infoSocket = InfoServer(addr, port)
        self.mSockPort = self.taskSocket.socket.getsockname()[1]

        # Init connection to fellow brokers
        #self.clusterSocket = self.context.socket(zmq.DEALER)
        #self.clusterSocket.setsockopt_string(zmq.IDENTITY, self.getName())

        #self.cluster = []
        #self.clusterAvailable = set()

        # Init statistics
        if self.debug:
            self.stats = []

        # Two cases are important and must be optimised:
        # - The search of unassigned task
        # - The search of available workers
        # These represent when the broker must deal the communications the
        # fastest. Other cases, the broker isn't flooded with urgent messages.

        # Initializing the queue of workers and tasks
        # The busy workers variable will contain a dict (map) of workers: task
        self.availableWorkers = deque()
        self.unassignedTasks = deque()
        self.groupTasks = defaultdict(list)
        # Shared variables containing {workerID:{varName:varVal},}
        self.sharedVariables = defaultdict(dict)

        # Start a worker-like communication if needed
        self.execQueue = None

        # Handle cloud-like behavior
        self.discoveryThread = None
        self.config = defaultdict(bool)
        self.processConfig({'headless': headless})

    def addBrokerList(self, aBrokerInfoList):
        """Add a broker to the broker cluster available list.
        Connects to the added broker if needed."""
        self.clusterAvailable.update(set(aBrokerInfoList))

        # If we need another connection to a fellow broker
        # TODO: only connect to a given number
        for aBrokerInfo in aBrokerInfoList:
            self.clusterSocket.connect(
                "tcp://{hostname}:{port}".format(
                    hostname=aBrokerInfo.hostname,
                    port=aBrokerInfo.task_port,
                )
            )
            self.cluster.append(aBrokerInfo)

    def processConfig(self, worker_config):
        """Update the pool configuration with a worker configuration.
        """
        self.config['headless'] |= worker_config.get("headless", False)
        if self.config['headless']:
            # Launch discovery process
            if not self.discoveryThread:
                self.discoveryThread = discovery.Advertise(
                    port=",".join(str(a) for a in self.getPorts()),
                )

    def run(self):
        """Redirects messages until a shutdown message is received.
        """
        asyncore.loop(timeout=0)
        self.shutdown()

    def getPorts(self):
        return (self.tSockPort, self.infoSockPort)

    def getName(self):
        import sys
        if sys.version < '3':
            return unicode(self.name)
        return self.name

    def shutdown(self):
        # This send may raise an ZMQError
        # Looping over it until it gets through
        for i in range(100):
            try:
                self.infoSocket.send(SHUTDOWN)
            except zmq.ZMQError:
                time.sleep(0.01)
            else:
                break
        time.sleep(0.1)

        self.taskSocket.close()
        self.infoSocket.close()
        #self.context.term()

        # Write down statistics about this run if asked
        if self.debug:
            import os
            import pickle
            try:
                os.mkdir('debug')
            except:
                pass
            name = self.name.replace(":", "_")
            with open("debug/broker-{name}".format(**locals()), 'wb') as f:
                pickle.dump(self.stats, f)
