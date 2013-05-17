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
from . import shared, encapsulation
import zmq
import scoop
import time
import sys
import random
try:
    import cPickle as pickle
except ImportError:
    import pickle


from .shared import SharedElementEncapsulation


class ReferenceBroken(Exception):
    """An object could not be unpickled (dereferenced) on a worker"""
    pass


class ZMQCommunicator(object):
    """This class encapsulates the communication features toward the broker."""
    context = zmq.Context()

    def __init__(self):
        # TODO number of broker
        self.number_of_broker = float('inf')
        self.broker_set = set()

        # socket for the futures, replies and request
        self.socket = ZMQCommunicator.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, scoop.WORKER_NAME)
        if zmq.zmq_version_info() >= (3, 0, 0):
            self.socket.setsockopt(zmq.RCVHWM, 0)
            self.socket.setsockopt(zmq.SNDHWM, 0)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        # socket for the shutdown signal
        self.infoSocket = ZMQCommunicator.context.socket(zmq.SUB)
        if zmq.zmq_version_info() >= (3, 0, 0):
            self.infoSocket.setsockopt(zmq.RCVHWM, 0)
            self.infoSocket.setsockopt(zmq.SNDHWM, 0)
        self.poller.register(self.infoSocket, zmq.POLLIN)
        self._addBroker(scoop.BROKER)

        # Send an INIT to get all previously set variables and share
        # current configuration to broker
        self.socket.send_multipart([
            b"INIT",
            pickle.dumps(scoop.CONFIGURATION)
        ])
        scoop.CONFIGURATION = pickle.loads(self.socket.recv())
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
        socks = dict(self.poller.poll(timeout))
        return self.socket in socks

    def _recv(self):
        msg = self.socket.recv_multipart()
        try:
            thisFuture = pickle.loads(msg[1])
        except AttributeError as e:
            scoop.logger.error(
                "An instance could not find its base reference on a worker. "
                "Ensure that your objects have their definition available in "
                "the root scope of your program.\n{error}".format(
                    error=e
                )
            )
            raise ReferenceBroken(e)
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
        socks = dict(self.poller.poll(0))
        while self.infoSocket in socks:
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
            elif msg[0] == b"ERASEBUFFER":
                scoop.reduction.cleanGroupID(pickle.loads(msg[1]))
            elif msg[0] == b"BROKER_INFO":
                #TODO: find out what to do here ...
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
                                        " were set.".format(scoop.WORKER_NAME,
                                                            self.number_of_broker)))

                    for broker in new_brokers:
                        broker_address = "tcp://" + broker.hostname + broker.task_port
                        meta_address = "tcp://" + broker.hostname + broker.info_port
                        self._addBroker(broker_address, meta_address)
                    self.broker_set.update(new_brokers)

            socks = dict(self.poller.poll(0))

    def convertVariable(self, key, varName, varValue):
        """Puts the function in the globals() of the main module."""
        if isinstance(varValue, encapsulation.FunctionEncapsulation):
            result = varValue.getFunction()

            # Update the global scope of the function to match the current module
            # TODO: Rework this not to be dependent on runpy / bootstrap call 
            # stack
            # TODO: Builtins doesn't work
            mainModule = sys.modules["__main__"]
            result.__name__ = varName
            result.__globals__.update(mainModule.__dict__)
            setattr(mainModule, varName, result)
            shared.elements[key].update({
                varName: result,
            })

    def recvFuture(self):
        while self._poll(0):
            yield self._recv()

    def sendFuture(self, future):
        try:
            if shared.getConst(future.callable.__name__,
                               timeout=0):
                # Enforce name reference passing if already shared
                future.callable = SharedElementEncapsulation(future.callable.__name__)
            self.socket.send_multipart([b"TASK",
                                        pickle.dumps(future,
                                                     pickle.HIGHEST_PROTOCOL)])
        except pickle.PicklingError as e:
            # If element not picklable, pickle its name
            # TODO: use its fully qualified name
            scoop.logger.warn("Pickling Error: {0}".format(e))
            previousCallable = future.callable
            future.callable = future.callable.__name__
            self.socket.send_multipart([b"TASK",
                                        pickle.dumps(future,
                                                     pickle.HIGHEST_PROTOCOL)])
            future.callable = previousCallable

    def sendResult(self, future):
        future.callable = None
        self.socket.send_multipart([b"REPLY",
                                    pickle.dumps(future,
                                                 pickle.HIGHEST_PROTOCOL),
                                    future.id.worker[0]])

    def sendVariable(self, key, value):
        self.socket.send_multipart([b"VARIABLE",
                                    pickle.dumps(key),
                                    pickle.dumps(value,
                                                 pickle.HIGHEST_PROTOCOL),
                                    pickle.dumps(scoop.worker,
                                                 pickle.HIGHEST_PROTOCOL)])

    def eraseBuffer(self, groupID):
        self.socket.send_multipart([b"ERASEBUFFER",
                                    pickle.dumps(groupID,
                                                 pickle.HIGHEST_PROTOCOL)])

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


class Shutdown(Exception):
    pass
