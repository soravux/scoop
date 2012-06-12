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
import sys
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
        self.context = zmq.Context(1)
        
        # zmq Socket for the tasks, replies and request.
        self.taskSocket = self.context.socket(zmq.ROUTER)
        self.taskSocket.bind(tSock)
        
        # zmq Socket for the shutdown TODO this is temporary
        self.infoSocket = self.context.socket(zmq.PUB)
        self.infoSocket.bind(mSock)

        # init self.poller
        self.poller = zmq.Poller()
        self.poller.register(self.taskSocket, zmq.POLLIN)
        self.poller.register(self.infoSocket, zmq.POLLIN)
        
        # init statistics
        if scoop.DEBUG:
            self.stats = []
        
        # Two cases are important and must be optimised:
        # - The search of unassigned task
        # - the search of available workers 
        # These represent when the broker must deal the communications the
        # fastest. Other cases, the broker isn't flooded with urgent messages.
        
        # Initializing the queue of workers and tasks
        # The busy workers variable will contain a dict (map) of workers: task
        self.busy_workers = {}
        self.available_workers = deque()
        self.unassigned_tasks = deque()

    def run(self):
        while True:
            socks = dict(self.poller.poll(-1))
            if (self.taskSocket in socks.keys() and socks[self.taskSocket] == zmq.POLLIN):
                msg = self.taskSocket.recv_multipart()
                msg_type = msg[1]
                # Broker received a new task
                if msg_type == TASK:
                    returnAddress = msg[0]
                    task = msg[2]
                    try:
                        address = self.available_workers.popleft()
                        self.busy_workers[address] = task
                        self.taskSocket.send_multipart([address, TASK, task])
                    except IndexError:
                        self.unassigned_tasks.append(task)
                        
                # Broker received a request for task
                elif msg_type == REQUEST:
                    address = msg[0]
                    if address in self.busy_workers:
                        del self.busy_workers[address]
                    
                    try:
                        task = self.unassigned_tasks.pop()
                        self.taskSocket.send_multipart([address, TASK, task])
                    except IndexError:
                        self.available_workers.append(address)
                
                # Broker received an answer needing delivery
                elif msg_type == REPLY:
                    address = msg[3]
                    task = msg[2]
                    self.taskSocket.send_multipart([address, REPLY, task])
                   
                elif msg_type == SHUTDOWN:
                    break
                    
                if scoop.DEBUG:
                    self.stats.append((time.time(), msg_type, len(self.unassigned_tasks), len(self.available_workers)))

    def shutdown(self):
        self.infoSocket.send(SHUTDOWN)
        # out of infinite loop: do some housekeeping
        time.sleep (0.3)
        
        self.taskSocket.close()
        self.infoSocket.close()
        self.context.term()
        
        # write down statistics about this run if asked
        if scoop.DEBUG:
            import os
            try:
                os.mkdir('debug')
            except:
                pass
            with open("debug/broker-" + scoop.BROKER_NAME, 'w') as f:
                f.write(str(self.stats))

if __name__=="__main__":
    port = str(5555) if len(sys.argv) < 2 else sys.argv[1]
    info_port = str(5556) if len(sys.argv) < 3 else sys.argv[2]
    this_broker = Broker("tcp://*:" + port, "tcp://*:" + info_port)
    try:
        this_broker.run()
    finally:
        this_broker.shutdown()
