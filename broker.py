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
from __future__ import print_function
import time
import zmq
from collections import deque
import scoop

REQUEST    = b"REQUEST"
TASK       = b"TASK"
REPLY      = b"REPLY"
SHUTDOWN   = b"SHUTDOWN"


class Broker(object):
    def __init__(self, tSock="tcp://*:5555", mSock="tcp://*:5556"):
        """This function initializes a broker.
    
    :param tSock: Task Socket Address. Must contain protocol, address and port
        information.
    :param mSock: Meta Socket Address. Must contain protocol, address and port
        information."""
        global context
        context = zmq.Context(1)
        
        # zmq Socket for the tasks, replies and request.
        self.taskSocket = context.socket(zmq.ROUTER)
        self.taskSocket.bind(tSock)
        
        # zmq Socket for the shutdown TODO this is temporary
        self.infoSocket = context.socket(zmq.PUB)
        self.infoSocket.bind(mSock)
        
        # Queue of available workers
        self.available_workers = 0
        self.workers_list = deque()

        # List of waiting tasks
        self.unassigned_tasks = deque()

        # init self.poller
        self.poller = zmq.Poller()
        self.poller.register(self.taskSocket, zmq.POLLIN)
        self.poller.register(self.infoSocket, zmq.POLLIN)
        
        # init statistics
        if scoop.DEBUG:
            self.stats = []

    def run(self):
        while True:
            socks = dict(self.poller.poll())
            if (self.taskSocket in socks.keys() and socks[self.taskSocket] == zmq.POLLIN):
                msg = self.taskSocket.recv_multipart()
                msg_type = msg[1]
                if msg_type == TASK:
                    returnAddress = msg[0]
                    task = msg[2]
                    if self.available_workers > 0:
                        self.available_workers -= 1
                        address = self.workers_list.pop()
                        self.taskSocket.send_multipart([address, TASK, task])
                    else:
                        self.unassigned_tasks.append(task)
                
                elif msg_type == REQUEST:
                    try:
                        address = msg[0]
                        task = self.unassigned_tasks.pop()
                        self.taskSocket.send_multipart([address, TASK, task])
                    except:
                        self.available_workers += 1
                        self.workers_list.append(msg[0])
                
                elif msg_type == REPLY:
                    address = msg[3]
                    task = msg[2]
                    self.taskSocket.send_multipart([address, REPLY, task])
                   
                elif msg_type == SHUTDOWN:
                    break
                    
                if scoop.DEBUG:
                    self.stats.append((time.time(), msg_type, len(self.unassigned_tasks), self.available_workers))

        self.infoSocket.send(SHUTDOWN)
        # out of infinite loop: do some housekeeping
        time.sleep (0.3)
        
        self.taskSocket.close()
        self.infoSocket.close()
        context.term()
        
        # write down statistics about this run if asked
        if scoop.DEBUG:
            with open("broker-" + scoop.BROKER_NAME, 'w') as f:
                f.write(str(self.stats))

if __name__=="__main__":
    this_broker = Broker()
    this_broker.run()
