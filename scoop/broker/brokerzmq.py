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
import copy
import logging
try:
    import cPickle as pickle
except ImportError:
    import pickle

import scoop
from scoop import TIME_BETWEEN_PARTIALDEBUG
from .. import discovery, utils
from .structs import BrokerInfo


# Worker requests
INIT = b"I"
REQUEST = b"RQ"
TASK = b"T"
REPLY = b"RP"
SHUTDOWN = b"S"
VARIABLE = b"V"
BROKER_INFO = b"B"
STATUS_REQ = b"SR"
STATUS_ANS = b"SA"
STATUS_DONE = b"SD"
STATUS_UPDATE = b"SU"

# Task statuses
STATUS_HERE = b"H"
STATUS_GIVEN = b"G"
STATUS_NONE = b"N"

# Broker interconnection
CONNECT = b"C"


class LaunchingError(Exception): pass


class Broker(object):
    def __init__(self, tSock="tcp://*:*", mSock="tcp://*:*", debug=False,
                 headless=False, hostname="127.0.0.1"):
        """This function initializes a broker.

        :param tSock: Task Socket Address.
        Must contain protocol, address  and port information.
        :param mSock: Meta Socket Address.
        Must contain protocol, address and port information.
        """
        # Initialize zmq
        self.context = zmq.Context(1)

        self.debug = debug
        self.hostname = hostname

        # zmq Socket for the tasks, replies and request.
        self.task_socket = self.context.socket(zmq.ROUTER)
        self.task_socket.setsockopt(zmq.IPV4ONLY, 0)
        self.task_socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
        self.task_socket.setsockopt(zmq.LINGER, 1000)
        self.t_sock_port = 0
        if tSock[-2:] == ":*":
            self.t_sock_port = self.task_socket.bind_to_random_port(tSock[:-2])
        else:
            self.task_socket.bind(tSock)
            self.t_sock_port = tSock.split(":")[-1]


        # Create identifier for this broker
        self.name = "{0}:{1}".format(hostname, self.t_sock_port)

        # Initialize broker logging
        self.logger = utils.initLogging(2 if debug else 0, name=self.name)
        self.logger.handlers[0].setFormatter(
            logging.Formatter(
                "[%(asctime)-15s] %(module)-9s ({0}) %(levelname)-7s "
                "%(message)s".format(self.name)
            )
        )

        # zmq Socket for the pool informations
        self.info_socket = self.context.socket(zmq.PUB)
        self.info_socket.setsockopt(zmq.IPV4ONLY, 0)
        self.info_socket.setsockopt(zmq.LINGER, 1000)
        self.info_sock_port = 0
        if mSock[-2:] == ":*":
            self.info_sock_port = self.info_socket.bind_to_random_port(mSock[:-2])
        else:
            self.info_socket.bind(mSock)
            self.info_sock_port = mSock.split(":")[-1]

        self.task_socket.setsockopt(zmq.SNDHWM, 0)
        self.task_socket.setsockopt(zmq.RCVHWM, 0)
        self.info_socket.setsockopt(zmq.SNDHWM, 0)
        self.info_socket.setsockopt(zmq.RCVHWM, 0)

        # Init connection to fellow brokers
        self.cluster_socket = self.context.socket(zmq.DEALER)
        self.cluster_socket.setsockopt(zmq.IPV4ONLY, 0)
        self.cluster_socket.setsockopt_string(zmq.IDENTITY, self.getName())
            
        self.cluster_socket.setsockopt(zmq.RCVHWM, 0)
        self.cluster_socket.setsockopt(zmq.SNDHWM, 0)
        self.cluster_socket.setsockopt(zmq.IMMEDIATE, 1)

        self.cluster = []
        self.cluster_available = set()

        # Init statistics
        if self.debug:
            self.stats = []
            self.lastDebugTs = time.time()

        # Two cases are important and must be optimised:
        # - The search of unassigned task
        # - The search of available workers
        # These represent when the broker must deal the communications the
        # fastest. Other cases, the broker isn't flooded with urgent messages.

        # Initializing the queue of workers and tasks
        # The busy workers variable will contain a dict (map) of workers: task
        self.available_workers = deque()
        self.unassigned_tasks = deque()
        self.assigned_tasks = defaultdict(set)
        self.status_times = {}
        # Shared variables containing {workerID:{varName:varVal},}
        self.shared_variables = defaultdict(dict)

        # Start a worker-like communication if needed
        self.execQueue = None

        # Handle cloud-like behavior
        self.discovery_thread = None
        self.config = defaultdict(bool)
        self.processConfig({'headless': headless})

    def addBrokerList(self, aBrokerInfoList):
        """Add a broker to the broker cluster available list.
        Connects to the added broker if needed."""
        self.cluster_available.update(set(aBrokerInfoList))

        # If we need another connection to a fellow broker
        # TODO: only connect to a given number
        for aBrokerInfo in aBrokerInfoList:
            self.cluster_socket.connect(
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
            if not self.discovery_thread:
                self.discovery_thread = discovery.Advertise(
                    port=",".join(str(a) for a in self.getPorts()),
                )

    def run(self):
        """Redirects messages until a shutdown message is received."""
        while True:
            if not self.task_socket.poll(-1):
                continue

            msg = self.task_socket.recv_multipart()
            msg_type = msg[1]

            if self.debug:
                self.stats.append((time.time(),
                                   msg_type,
                                   len(self.unassigned_tasks),
                                   len(self.available_workers)))
                if time.time() - self.lastDebugTs > TIME_BETWEEN_PARTIALDEBUG:
                    self.writeDebug("debug/partial-{0}".format(
                        round(time.time(), -1)
                    ))
                    self.lastDebugTs = time.time()

            # New task inbound
            if msg_type == TASK:
                task_id = msg[2]
                task = msg[3]
                self.logger.debug("Received task {0}".format(task_id))
                try:
                    address = self.available_workers.popleft()
                except IndexError:
                    self.unassigned_tasks.append((task_id, task))
                else:
                    self.logger.debug("Sent {0}".format(task_id))
                    self.task_socket.send_multipart([address, TASK, task])
                    self.assigned_tasks[address].add(task_id)

            # Request for task
            elif msg_type == REQUEST:
                address = msg[0]
                try:
                    task_id, task = self.unassigned_tasks.popleft()
                except IndexError:
                    self.available_workers.append(address)
                else:
                    self.logger.debug("Sent {0}".format(task_id))
                    self.task_socket.send_multipart([address, TASK, task])
                    self.assigned_tasks[address].add(task_id)

            # A task status request is requested
            elif msg_type == STATUS_REQ:
                self.pruneAssignedTasks()
                address = msg[0]
                task_id = msg[2]

                if any(task_id in x for x in self.assigned_tasks.values()):
                    status = STATUS_GIVEN
                elif task_id in (x[0] for x in self.unassigned_tasks):
                    status = STATUS_HERE
                else:
                    status = STATUS_NONE

                self.task_socket.send_multipart([
                    address, STATUS_ANS, task_id, status
                ])

            # A task status set (task done) is received
            elif msg_type == STATUS_DONE:
                address = msg[0]
                task_id = msg[2]

                try:
                    self.assigned_tasks[address].discard(task_id)
                except KeyError:
                    pass

            elif msg_type == STATUS_UPDATE:
                address = msg[0]
                try:
                    tasks_ids = pickle.loads(msg[2])
                except:
                    self.logger.error("Could not unpickle status update message.")
                else:
                    self.assigned_tasks[address] = tasks_ids
                    self.status_times[address] = time.time()

            # Answer needing delivery
            elif msg_type == REPLY:
                self.logger.debug("Relaying")
                destination = msg[-1]
                origin = msg[0]
                self.task_socket.send_multipart([destination] + msg[1:] + [origin])

            # Shared variable to distribute
            elif msg_type == VARIABLE:
                address = msg[4]
                value = msg[3]
                key = msg[2]
                self.shared_variables[address].update(
                    {key: value},
                )
                self.info_socket.send_multipart([VARIABLE,
                                                key,
                                                value,
                                                address])

            # Initialize the variables of a new worker
            elif msg_type == INIT:
                address = msg[0]
                try:
                    self.processConfig(pickle.loads(msg[2]))
                except pickle.PickleError:
                    continue
                self.task_socket.send_multipart([
                    address,
                    pickle.dumps(self.config,
                                 pickle.HIGHEST_PROTOCOL),
                    pickle.dumps(self.shared_variables,
                                 pickle.HIGHEST_PROTOCOL),
                ])

                self.task_socket.send_multipart([
                    address,
                    pickle.dumps(self.cluster_available,
                                 pickle.HIGHEST_PROTOCOL),
                ])

            # Add a given broker to its fellow list
            elif msg_type == CONNECT:
                try:
                    connect_brokers = pickle.loads(msg[2])
                except pickle.PickleError:
                    self.logger.error("Could not understand CONNECT message.")
                    continue
                self.logger.info("Connecting to other brokers...")
                self.addBrokerList(connect_brokers)

            # Shutdown of this broker was requested
            elif msg_type == SHUTDOWN:
                self.logger.debug("SHUTDOWN command received.")
                self.shutdown()
                break

    def pruneAssignedTasks(self):
        to_keep = set()
        for address in self.assigned_tasks.keys():
            addr_time = self.status_times.get(address, 0)
            if addr_time + scoop.TIME_BETWEEN_STATUS_PRUNING > time.time():
                to_keep.add(address)

        to_remove = set(self.assigned_tasks.keys()).difference(to_keep)
        for addr in to_remove:
            self.assigned_tasks.pop(addr)

        to_remove = set(self.status_times.keys()).difference(to_keep)
        for addr in to_remove:
            self.status_times.pop(addr)

    def getPorts(self):
        return (self.t_sock_port, self.info_sock_port)

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
                self.info_socket.send(SHUTDOWN)
            except zmq.ZMQError:
                time.sleep(0.01)
            else:
                break
        time.sleep(0.1)

        self.context.destroy(1000)

        # Write down statistics about this run if asked
        if self.debug:
            self.writeDebug()

    def writeDebug(self, path="debug"):
        import os
        import pickle
        try:
            os.makedirs(path)
        except:
            pass
        name = self.name.replace(":", "_")
        with open(os.path.join(
                path,
                "broker-{name}".format(**locals())), 'wb') as f:
            pickle.dump(self.stats, f)
