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
        if scoop.IS_ORIGIN is False:
            self.infoSocket.connect(scoop.META_ADDRESS)
            self.infoSocket.setsockopt(zmq.SUBSCRIBE, b"")
            self.poller.register(self.infoSocket, zmq.POLLIN)

    def _poll(self, timeout):
        socks = dict(self.poller.poll(timeout))
        if self.infoSocket in socks:
            raise Shutdown("Closing the communication")
        elif self.socket in socks:
            return True
        else:
            return False

    def _recv(self):
        msg = self.socket.recv_multipart()
        return pickle.loads(msg[1])

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
