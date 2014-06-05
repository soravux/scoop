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
import asyncore
import array
import threading
try:
    import cPickle as pickle
except ImportError:
    import pickle

import scoop
from .. import shared, encapsulation, utils
from ..shared import SharedElementEncapsulation
from .scoopexceptions import Shutdown, ReferenceBroken

try:
    _chr = unichr
except NameError:
    scoop.logger.warn('NameError on scooptcp.')
    _chr = chr


def serialize(*data):
    #sendData = ''.join(data)
    #sendData = _chr(len(sendData)) + sendData
    #return array.array('b', sendData).tobytes()
    return pickle.dumps(data)

def deserialize(data):
    #return array.frombytes(data)
    return pickle.loads(data)


class EchoHandler(asyncore.dispatcher_with_send):

    def handle_read(self):
        data = self.recv(8192)
        if data:
            self.send(data)

class DirectSocketServer(asyncore.dispatcher):
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
            handler = EchoHandler(sock)


class TCPCommunicator(object):
    """This class encapsulates the communication features toward the broker."""

    def __init__(self):
        # TODO number of broker
        self.number_of_broker = float('inf')
        self.broker_set = set()

        # Get the current address of the interface facing the broker
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((scoop.BROKER.externalHostname, scoop.BROKER.task_port))
        external_addr = s.getsockname()[0]
        s.close()

        if external_addr in utils.loopbackReferences:
            external_addr = scoop.BROKER.externalHostname

        # Create an inter-worker socket
        self.direct_socket_peers = []
        self.direct_socket = DirectSocketServer('', 0)
        self.direct_socket_port = self.direct_socket.getsockname()[1]

        scoop.worker = "{addr}:{port}".format(
            addr=external_addr,
            port=self.direct_socket_port,
        ).encode()

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
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # socket for the shutdown signal
        #self.infoSocket = CreateZMQSocket(zmq.SUB)
        
        # Set poller
        #self.poller = zmq.Poller()
        #self.poller.register(self.socket, zmq.POLLIN)
        #self.poller.register(self.direct_socket, zmq.POLLIN)
        #self.poller.register(self.infoSocket, zmq.POLLIN)

        self._addBroker(scoop.BROKER)

        # Send an INIT to get all previously set variables and share
        # current configuration to broker
        self.socket.send(serialize(
            b"INIT",
            pickle.dumps(scoop.CONFIGURATION),
        ))
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

        self.OPEN = True

        self.loop_thread = threading.Thread(target=asyncore.loop,
                                            name="Asyncore Loop")
        self.loop_thread.daemon = True
        self.loop_thread.start()

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
        except AttributeError as e:
            scoop.logger.error(
                "An instance could not find its base reference on a worker. "
                "Ensure that your objects have their definition available in "
                "the root scope of your program.\n{error}".format(
                    error=e,
                )
            )
            raise ReferenceBroken(e)

        if msg[0] == b"TASK":
            # Try to connect directly to this worker to send the result
            # afterwards if Future is from a map.
            if thisFuture.sendResultBack:
                self.addPeer(thisFuture.id.worker)

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
        while self.infoSocket.poll(0):
            msg = self.infoSocket.recv_multipart()
            if msg[0] == b"SHUTDOWN":
                if scoop.IS_ORIGIN is False:
                    raise Shutdown("Shutdown received")
                if not scoop.SHUTDOWN_REQUESTED:
                    scoop.logger.error(
                        "A worker exited unexpectedly. Read the worker logs "
                        "for more information. SCOOP pool will now shutdown."
                    )
                    raise Shutdown("Unexpected shutdown received")
            elif msg[0] == b"VARIABLE":
                key = pickle.loads(msg[3])
                varValue = pickle.loads(msg[2])
                varName = pickle.loads(msg[1])
                shared.elements.setdefault(key, {}).update({varName: varValue})
                self.convertVariable(key, varName, varValue)
            elif msg[0] == b"BROKER_INFO":
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
        try:
            if shared.getConst(hash(future.callable),
                               timeout=0):
                # Enforce name reference passing if already shared
                future.callable = SharedElementEncapsulation(hash(future.callable))
            self.socket.send_multipart([b"TASK",
                                        pickle.dumps(future,
                                                     pickle.HIGHEST_PROTOCOL)])
        except pickle.PicklingError as e:
            # If element not picklable, pickle its name
            # TODO: use its fully qualified name
            scoop.logger.warn("Pickling Error: {0}".format(e))
            previousCallable = future.callable
            future.callable = hash(future.callable)
            self.socket.send_multipart([b"TASK",
                                        pickle.dumps(future,
                                                     pickle.HIGHEST_PROTOCOL)])
            future.callable = previousCallable

    def sendResult(self, future):
        """Send a terminated future back to its parent."""
        future = copy.copy(future)

        # Remove the (now) extraneous elements from future class
        future.callable = future.args = future.kargs = future.greenlet = None

        if not future.sendResultBack:
            # Don't reply back the result if it isn't asked
            future.resultValue = None

        self._sendReply(
            future.id.worker,
            pickle.dumps(
                future,
                pickle.HIGHEST_PROTOCOL,
            ),
        )

    def _sendReply(self, destination, *args):
        """Send a REPLY directly to its destination. If it doesn't work, launch
        it back to the broker."""
        # Try to send the result directly to its parent
        self.addPeer(destination)

        try:
            self.direct_socket.send_multipart([
                destination,
                b"REPLY",
            ] + list(args),
                flags=zmq.NOBLOCK)
        except zmq.error.ZMQError as e:
            # Fallback on Broker routing if no direct connection possible
            scoop.logger.debug(
                "{0}: Could not send result directly to peer {1}, routing through "
                "broker.".format(scoop.worker, destination)
            )
            self.socket.send_multipart([
                b"REPLY", 
                ] + list(args) + [
                destination,
            ])

    def sendVariable(self, key, value):
        self.socket.send_multipart([b"VARIABLE",
                                    pickle.dumps(key),
                                    pickle.dumps(value,
                                                 pickle.HIGHEST_PROTOCOL),
                                    pickle.dumps(scoop.worker,
                                                 pickle.HIGHEST_PROTOCOL)])

    def taskEnd(self, groupID, askResults=False):
        self.socket.send_multipart([
            b"TASKEND",
            pickle.dumps(
                askResults,
                pickle.HIGHEST_PROTOCOL
            ),
            pickle.dumps(
                groupID,
                pickle.HIGHEST_PROTOCOL
            ),
        ])

    def sendRequest(self):
        for _ in range(len(self.broker_set)):
            self.socket.send(b"REQUEST")

    def workerDown(self):
        self.socket.send(b"WORKERDOWN")

    def shutdown(self):
        """Sends a shutdown message to other workers."""
        if self.OPEN:
            self.OPEN = False
            scoop.SHUTDOWN_REQUESTED = True
            self.socket.send(b"SHUTDOWN")
            self.socket.close()
            self.infoSocket.close()
            time.sleep(0.3)
