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
import zmq
import sys
import threading
try:
    import cPickle as pickle
except ImportError:
    import pickle

from .. import discovery

INIT = b"INIT"
REQUEST = b"REQUEST"
TASK = b"TASK"
REPLY = b"REPLY"
SHUTDOWN = b"SHUTDOWN"
VARIABLE = b"VARIABLE"
ERASEBUFFER = b"ERASEBUFFER"


class Broker(object):
    def __init__(self, tSock="tcp://*:*", mSock="tcp://*:*", debug=False,
                 headless=False):
        """This function initializes a broker.

        :param tSock: Task Socket Address.
        Must contain protocol, address  and port information.
        :param mSock: Meta Socket Address.
        Must contain protocol, address and port information.
        """
        self.context = zmq.Context(1)

        self.debug = debug

        # zmq Socket for the tasks, replies and request.
        self.taskSocket = self.context.socket(zmq.ROUTER)
        self.tSockPort = 0
        if tSock[-2:] == ":*":
            self.tSockPort = self.taskSocket.bind_to_random_port(tSock[:-2])
        else:
            self.taskSocket.bind(tSock)

        # zmq Socket for the shutdown TODO this is temporary
        self.infoSocket = self.context.socket(zmq.PUB)
        self.infoSockPort = 0
        if mSock[-2:] == ":*":
            self.infoSockPort = self.infoSocket.bind_to_random_port(mSock[:-2])
        else:
            self.infoSocket.bind(mSock)

        if zmq.zmq_version_info() >= (3, 0, 0):
            self.taskSocket.setsockopt(zmq.SNDHWM, 0)
            self.taskSocket.setsockopt(zmq.RCVHWM, 0)
            self.infoSocket.setsockopt(zmq.SNDHWM, 0)
            self.infoSocket.setsockopt(zmq.RCVHWM, 0)

        # init self.poller
        self.poller = zmq.Poller()
        self.poller.register(self.taskSocket, zmq.POLLIN)
        self.poller.register(self.infoSocket, zmq.POLLIN)

        # init statistics
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
        # Shared variables containing {workerID:{varName:varVal},}
        self.sharedVariables = defaultdict(dict)

        self.config = defaultdict(bool)
        self.processConfig({'headless': headless})

        self.discoveryThread = None

    def processConfig(self, worker_config):
        """Update the pool configuration with a worker configuration.
        """
        self.config['headless'] |= worker_config.get("headless", False)
        if self.config['headless']:
            # Launch discovery process
            if not self.discoveryThread:
                self.discoveryThread = threading.Thread(
                    target=discovery.Advertise,
                    kwargs={"port":",".join(str(a) for a in self.getPorts()),
                            "location":"",
                            },
                )
                self.discoveryThread.start()

    def run(self):
        """Redirects messages until a shutdown messages is received.
        """
        while True:
            socks = dict(self.poller.poll(-1))
            if not (self.taskSocket in socks.keys()
            and socks[self.taskSocket] == zmq.POLLIN):
                continue

            msg = self.taskSocket.recv_multipart()
            msg_type = msg[1]

            if self.debug:
                self.stats.append((time.time(),
                                   msg_type,
                                   len(self.unassignedTasks),
                                   len(self.availableWorkers)))

            # New task inbound
            if msg_type == TASK:
                returnAddress = msg[0]
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
                address = msg[3]
                task = msg[2]
                self.taskSocket.send_multipart([address, REPLY, task])

            # Shared variable to distribute
            elif msg_type == VARIABLE:
                address = msg[3]
                variable = msg[2]
                try:
                    self.sharedVariables[address].update(
                        pickle.loads(variable)
                    )
                except pickle.PickleError:
                    # Just forget the bad variable
                    continue
                self.infoSocket.send_multipart([VARIABLE,
                                                variable,
                                                address])

            # Initialize the variables of a new worker
            elif msg_type == INIT:
                address = msg[0]
                try:
                    self.processConfig(pickle.loads(msg[2]))
                except pickle.PickleError:
                    continue
                self.taskSocket.send_multipart([
                    address,
                    pickle.dumps(self.config,
                                 pickle.HIGHEST_PROTOCOL),
                    pickle.dumps(self.sharedVariables,
                                 pickle.HIGHEST_PROTOCOL),
                ])

            # Clean the buffers when a coherent (mapReduce/mapScan)
            # operation terminates
            elif msg_type == ERASEBUFFER:
                groupID = msg[2]
                self.infoSocket.send_multipart([ERASEBUFFER,
                                                groupID])

            elif msg_type == SHUTDOWN:
                self.shutdown()
                break

    def getPorts(self):
        return (self.tSockPort, self.infoSockPort)

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
        self.context.term()

        # Write down statistics about this run if asked
        if self.debug:
            import os
            import pickle
            try:
                os.mkdir('debug')
            except:
                pass
            with open("debug/broker-broker", 'wb') as f:
                pickle.dump(self.stats, f)
