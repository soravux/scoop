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
from __future__ import print_function
from . import manager
import zmq
import scoop
import time
try:
    import cPickle as pickle
except ImportError:
    import pickle


class ZMQCommunicator(object):
    """This class encapsulates the communication features toward the broker."""
    context = zmq.Context()

    def __init__(self):
        # socket for the futures, replies and request
        self.socket = ZMQCommunicator.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, scoop.WORKER_NAME)
        self.socket.connect(scoop.BROKER_ADDRESS)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        # socket for the shutdown signal
        self.infoSocket = ZMQCommunicator.context.socket(zmq.SUB)
        self.infoSocket.connect(scoop.META_ADDRESS)
        self.infoSocket.setsockopt(zmq.SUBSCRIBE, b"")
        self.poller.register(self.infoSocket, zmq.POLLIN)

        # Send an INIT to get all previously set variables
        self.socket.send(b"INIT")
        manager.Manager.elements = pickle.loads(self.socket.recv())

    def _poll(self, timeout):
        self.pumpInfoSocket()
        socks = dict(self.poller.poll(timeout))
        return self.socket in socks

    def _recv(self):
        msg = self.socket.recv_multipart()
        return pickle.loads(msg[1])

    def pumpInfoSocket(self):
        socks = dict(self.poller.poll(0))
        while self.infoSocket in socks:
            msg = self.infoSocket.recv_multipart()
            if msg[0] == b"SHUTDOWN" and scoop.IS_ORIGIN is False:
                raise Shutdown("Shutdown received")
            elif msg[0] == b"VARIABLE":
                key = pickle.loads(msg[2])
                value = pickle.loads(msg[1])
                manager.Manager.elements.get(key, {}).update(value)
            socks = dict(self.poller.poll(0))

    def recvFuture(self):
        while self._poll(0):
            yield self._recv()

    def sendFuture(self, future):
        self.socket.send_multipart([b"TASK",
                                    pickle.dumps(future,
                                                 pickle.HIGHEST_PROTOCOL)])

    def sendResult(self, future):
        self.socket.send_multipart([b"REPLY",
                                    pickle.dumps(future,
                                                 pickle.HIGHEST_PROTOCOL),
                                    future.id.worker[0]])

    def sendVariable(self, element):
        self.socket.send_multipart([b"VARIABLE",
                                    pickle.dumps(element,
                                                 pickle.HIGHEST_PROTOCOL),
                                    pickle.dumps(scoop.worker,
                                                 pickle.HIGHEST_PROTOCOL)])

    def sendRequest(self):
        self.socket.send(b"REQUEST")

    def shutdown(self):
        """Sends a shutdown message to other workers."""
        self.socket.send(b"SHUTDOWN")
        self.socket.close()
        self.infoSocket.close()
        time.sleep(0.3)


class Shutdown(Exception):
    pass