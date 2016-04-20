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
import time
import sys
import random
import socket
import copy
import logging
import threading
try:
    import cPickle as pickle
except ImportError:
    import pickle

import zmq

import scoop
from .. import shared, encapsulation, utils
from ..shared import SharedElementEncapsulation
from .scoopexceptions import Shutdown, ReferenceBroken

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


LINGER_TIME = 1000


class ZMQCommunicator(object):
    """This class encapsulates the communication features toward the broker."""

    def __init__(self):
        self.ZMQcontext = zmq.Context()

        # TODO number of broker
        self.number_of_broker = float('inf')
        self.broker_set = set()


        # Get the current address of the interface facing the broker
        info = socket.getaddrinfo(scoop.BROKER.externalHostname, scoop.BROKER.task_port)[0]
        s = socket.socket(info[0], socket.SOCK_DGRAM)
        s.connect(info[4][:2])
        external_addr = s.getsockname()[0]
        s.close()

        if external_addr in utils.loopbackReferences or info[0] == socket.AF_INET6:
            external_addr = scoop.BROKER.externalHostname

        # Create an inter-worker socket
        self.direct_socket_peers = []
        self.direct_socket = self.createZMQSocket(zmq.ROUTER)
        # TODO: This doesn't seems to be respected in the ROUTER socket
        self.direct_socket.setsockopt(zmq.SNDTIMEO, 0)
        # Code stolen from pyzmq's bind_to_random_port() from sugar/socket.py
        for i in range(100):
            try:
                self.direct_socket_port = random.randrange(49152, 65536)
                # Set current worker inter-worker socket name to its addr:port
                scoop.worker = "{addr}:{port}".format(
                    addr=external_addr,
                    port=self.direct_socket_port,
                ).encode()
                self.direct_socket.setsockopt(zmq.IDENTITY, scoop.worker)
                self.direct_socket.bind("tcp://*:{0}".format(
                    self.direct_socket_port,
                ))
            except:
                # Except on ZMQError with a check on EADDRINUSE should go here
                # but its definition is not consistent in pyzmq over multiple
                # versions
                pass
            else:
                break
        else:
            raise Exception("Could not create direct connection socket")

        # Update the logger to display our name
        try:
            scoop.logger.handlers[0].setFormatter(
                logging.Formatter(
                    "[%(asctime)-15s] %(module)-9s ({0}) %(levelname)-7s "
                    "%(message)s".format(scoop.worker)
                )
            )
        except IndexError:
            scoop.logger.debug(
                "Could not set worker name into logger ({0})".format(
                    scoop.worker
                )
            )

        # socket for the futures, replies and request
        self.socket = self.createZMQSocket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, scoop.worker)

        # socket for the shutdown signal
        self.infoSocket = self.createZMQSocket(zmq.SUB)

        # Set poller
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.poller.register(self.direct_socket, zmq.POLLIN)
        self.poller.register(self.infoSocket, zmq.POLLIN)

        self._addBroker(scoop.BROKER)

        # Send an INIT to get all previously set variables and share
        # current configuration to broker
        self.socket.send_multipart([
            INIT,
            pickle.dumps(scoop.CONFIGURATION)
        ])
        scoop.CONFIGURATION.update(pickle.loads(self.socket.recv()))
        inboundVariables = pickle.loads(self.socket.recv())
        shared.elements = dict([
            (pickle.loads(key),
                dict([(pickle.loads(varName),
                       pickle.loads(varValue))
                    for varName, varValue in value.items()
                ]))
                for key, value in inboundVariables.items()
        ])
        for broker in pickle.loads(self.socket.recv()):
            # Skip already connected brokers
            if broker in self.broker_set:
                continue
            self._addBroker(broker)

        # Putting futures status reporting in place
        self.status_update_thread = threading.Thread(target=self._reportFutures)
        self.status_update_thread.daemon = True
        self.status_update_thread.start()

    def createZMQSocket(self, sock_type):
        """Create a socket of the given sock_type and deactivate message dropping"""
        sock = self.ZMQcontext.socket(sock_type)
        sock.setsockopt(zmq.LINGER, LINGER_TIME)
        sock.setsockopt(zmq.IPV4ONLY, 0)

        # Remove message dropping
        sock.setsockopt(zmq.SNDHWM, 0)
        sock.setsockopt(zmq.RCVHWM, 0)
        try:
            sock.setsockopt(zmq.IMMEDIATE, 1)
        except:
            # This parameter was recently added by new libzmq versions
            pass

        # Don't accept unroutable messages
        if sock_type == zmq.ROUTER:
            sock.setsockopt(zmq.ROUTER_MANDATORY, 1)
        return sock

    def _reportFutures(self):
        """Sends futures status updates to broker at intervals of
        scoop.TIME_BETWEEN_STATUS_REPORTS seconds. Is intended to be run by a
        separate thread."""
        try:
            while True:
                time.sleep(scoop.TIME_BETWEEN_STATUS_REPORTS)
                fids = set(x.id for x in scoop._control.execQueue.movable)
                fids.update(set(x.id for x in scoop._control.execQueue.ready))
                fids.update(set(x.id for x in scoop._control.execQueue.inprogress))
                self.socket.send_multipart([
                    STATUS_UPDATE,
                    pickle.dumps(fids),
                ])
        except AttributeError:
            # The process is being shut down.
            pass

    def addPeer(self, peer):
        if peer not in self.direct_socket_peers:
            self.direct_socket_peers.append(peer)
            new_peer = "tcp://{0}".format(peer.decode("utf-8"))
            self.direct_socket.connect(new_peer)

    def _addBroker(self, brokerEntry):
        # Add a broker to the socket and the infosocket.
        broker_address = "tcp://{hostname}:{port}".format(
            hostname=brokerEntry.hostname,
            port=brokerEntry.task_port,
        )
        meta_address = "tcp://{hostname}:{port}".format(
            hostname=brokerEntry.hostname,
            port=brokerEntry.info_port,
        )
        self.socket.connect(broker_address)

        self.infoSocket.connect(meta_address)
        self.infoSocket.setsockopt(zmq.SUBSCRIBE, b"")

        self.broker_set.add(brokerEntry)

    def _poll(self, timeout):
        self.pumpInfoSocket()
        return self.poller.poll(timeout)

    def _recv(self):
        # Prioritize answers over new tasks
        if self.direct_socket.poll(0):
            router_msg = self.direct_socket.recv_multipart()
            # Remove the sender address
            msg = router_msg[1:] + [router_msg[0]]
        else:
            msg = self.socket.recv_multipart()
        
        try:
            thisFuture = pickle.loads(msg[1])
        except (AttributeError, ImportError) as e:
            scoop.logger.error(
                "An instance could not find its base reference on a worker. "
                "Ensure that your objects have their definition available in "
                "the root scope of your program.\n{error}".format(
                    error=e,
                )
            )
            raise ReferenceBroken(e)

        if msg[0] == TASK:
            # Try to connect directly to this worker to send the result
            # afterwards if Future is from a map.
            if thisFuture.sendResultBack:
                self.addPeer(thisFuture.id[0])

        elif msg[0] == STATUS_ANS:
            # TODO: This should not be here but in FuturesQueue.
            if msg[2] == STATUS_HERE:
                # TODO: Don't know why should that be done?
                self.sendRequest()
            elif msg[2] == STATUS_NONE:
                # If a task was requested but is nowhere to be found, resend it
                future_id = pickle.loads(msg[1])
                try:
                    scoop.logger.warning(
                        "Lost track of future {0}. Resending it..."
                        "".format(scoop._control.futureDict[future_id])
                    )
                    self.sendFuture(scoop._control.futureDict[future_id])
                except KeyError:
                    # Future was received and processed meanwhile
                    pass
            return

        isCallable = callable(thisFuture.callable)
        isDone = thisFuture._ended()
        if not isCallable and not isDone:
            # TODO: Also check in root module globals for fully qualified name
            try:
                module_found = hasattr(sys.modules["__main__"],
                                       thisFuture.callable)
            except TypeError:
                module_found = False
            if module_found:
                thisFuture.callable = getattr(sys.modules["__main__"],
                                              thisFuture.callable)
            else:
                raise ReferenceBroken("This element could not be pickled: "
                                      "{0}.".format(thisFuture))
        return thisFuture

    def pumpInfoSocket(self):
        try:
            while self.infoSocket.poll(0):
                msg = self.infoSocket.recv_multipart()
                if msg[0] == SHUTDOWN:
                    if scoop.IS_ORIGIN is False:
                        raise Shutdown("Shutdown received")
                    if not scoop.SHUTDOWN_REQUESTED:
                        scoop.logger.error(
                            "A worker exited unexpectedly. Read the worker logs "
                            "for more information. SCOOP pool will now shutdown."
                        )
                        raise Shutdown("Unexpected shutdown received")
                elif msg[0] == VARIABLE:
                    key = pickle.loads(msg[3])
                    varValue = pickle.loads(msg[2])
                    varName = pickle.loads(msg[1])
                    shared.elements.setdefault(key, {}).update({varName: varValue})
                    self.convertVariable(key, varName, varValue)
                elif msg[0] == BROKER_INFO:
                    # TODO: find out what to do here ...
                    if len(self.broker_set) == 0: # The first update
                        self.broker_set.add(pickle.loads(msg[1]))
                    if len(self.broker_set) < self.number_of_broker:
                        brokers = pickle.loads(msg[2])
                        needed = self.number_of_broker - len(self.broker_set)
                        try:
                            new_brokers = random.sample(brokers, needed)
                        except ValueError:
                            new_brokers = brokers
                            self.number_of_broker = len(self.broker_set) + len(new_brokers)
                            scoop.logger.warning(("The number of brokers could not be set"
                                            " on worker {0}. A total of {1} worker(s)"
                                            " were set.".format(scoop.worker,
                                                                self.number_of_broker)))

                        for broker in new_brokers:
                            broker_address = "tcp://" + broker.hostname + broker.task_port
                            meta_address = "tcp://" + broker.hostname + broker.info_port
                            self._addBroker(broker_address, meta_address)
                        self.broker_set.update(new_brokers)
        except zmq.error.ZMQError:
            pass

    def convertVariable(self, key, varName, varValue):
        """Puts the function in the globals() of the main module."""
        if isinstance(varValue, encapsulation.FunctionEncapsulation):
            result = varValue.getFunction()

            # Update the global scope of the function to match the current module
            mainModule = sys.modules["__main__"]
            result.__name__ = varName
            result.__globals__.update(mainModule.__dict__)
            setattr(mainModule, varName, result)
            shared.elements[key].update({
                varName: result,
            })

    def recvFuture(self):
        while self._poll(0):
            received = self._recv()
            if received:
                yield received

    def sendFuture(self, future):
        """Send a Future to be executed remotely."""
        future = copy.copy(future)
        future.greenlet = None
        future.children = {}

        try:
            if shared.getConst(hash(future.callable), timeout=0):
                # Enforce name reference passing if already shared
                future.callable = SharedElementEncapsulation(hash(future.callable))
            self.socket.send_multipart([
                TASK,
                pickle.dumps(future.id, pickle.HIGHEST_PROTOCOL),
                pickle.dumps(future, pickle.HIGHEST_PROTOCOL),
            ])
        except (pickle.PicklingError, TypeError) as e:
            # If element not picklable, pickle its name
            # TODO: use its fully qualified name
            scoop.logger.warn("Pickling Error: {0}".format(e))
            future.callable = hash(future.callable)
            self.socket.send_multipart([
                TASK,
                pickle.dumps(future.id, pickle.HIGHEST_PROTOCOL),
                pickle.dumps(future, pickle.HIGHEST_PROTOCOL),
            ])

    def sendResult(self, future):
        """Send a terminated future back to its parent."""
        future = copy.copy(future)

        # Remove the (now) extraneous elements from future class
        future.callable = future.args = future.kargs = future.greenlet = None

        if not future.sendResultBack:
            # Don't reply back the result if it isn't asked
            future.resultValue = None

        self._sendReply(
            future.id[0],
            pickle.dumps(future.id, pickle.HIGHEST_PROTOCOL),
            pickle.dumps(future, pickle.HIGHEST_PROTOCOL),
        )

    def _sendReply(self, destination, fid, *args):
        """Send a REPLY directly to its destination. If it doesn't work, launch
        it back to the broker."""
        # Try to send the result directly to its parent
        self.addPeer(destination)

        try:
            self.direct_socket.send_multipart([
                destination,
                REPLY,
            ] + list(args),
                flags=zmq.NOBLOCK)
        except zmq.error.ZMQError as e:
            # Fallback on Broker routing if no direct connection possible
            scoop.logger.debug(
                "{0}: Could not send result directly to peer {1}, routing through "
                "broker.".format(scoop.worker, destination)
            )
            self.socket.send_multipart([
                REPLY, 
                ] + list(args) + [
                destination,
            ])

        self.socket.send_multipart([
            STATUS_DONE,
            fid,
        ])

    def sendStatusRequest(self, future):
        self.socket.send_multipart([
            STATUS_REQ,
            pickle.dumps(future.id, pickle.HIGHEST_PROTOCOL),
        ])

    def sendVariable(self, key, value):
        self.socket.send_multipart([
            VARIABLE,
            pickle.dumps(key, pickle.HIGHEST_PROTOCOL),
            pickle.dumps(value, pickle.HIGHEST_PROTOCOL),
            pickle.dumps(scoop.worker, pickle.HIGHEST_PROTOCOL),
        ])

    def sendRequest(self):
        for _ in range(len(self.broker_set)):
            self.socket.send(REQUEST)

    def workerDown(self):
        self.socket.send(WORKERDOWN)

    def shutdown(self):
        """Sends a shutdown message to other workers."""
        if self.ZMQcontext and not self.ZMQcontext.closed:
            scoop.SHUTDOWN_REQUESTED = True
            self.socket.send(SHUTDOWN)
            
            # pyzmq would issue an 'no module named zmqerror' on windows
            # without this
            try:
                self.direct_socket.__del__()
                self.socket.__del__()
                self.infoSocket.__del__()
            except AttributeError:
                # Older versions of pyzmq doesn't have the __del__ method
                pass

            self.ZMQcontext.destroy()
