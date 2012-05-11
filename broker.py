#!/usr/bin/env python
from __future__ import print_function
import time
import cPickle as pickle
import zmq
from collections import deque

url        = "tcp://*:5555"
url2       = "tcp://*:5556"
REQUEST    = "REQUEST"
TASK       = "TASK"
REPLY      = "REPLY"

if __name__=="__main__":

    context = zmq.Context(1)
    
    # zmq Socket for the tasks, replies and request.
    taskSocket = context.socket(zmq.ROUTER)
    taskSocket.bind(url)
    
    # zmq Socket for the shutdown TODO this is temporary
    infoSocket = context.socket(zmq.PUB)
    infoSocket.bind(url2)
    
    # Queue of available workers
    available_workers = 0
    workers_list = deque()#[]

    # List of waiting tasks
    unassigned_tasks = deque()#[]

    # init poller
    poller = zmq.Poller()
    poller.register(taskSocket, zmq.POLLIN)
    poller.register(infoSocket, zmq.POLLIN)


    while True:
        
        socks = dict(poller.poll())      
        if (taskSocket in socks.keys() and socks[taskSocket] == zmq.POLLIN):
                    
            msg = taskSocket.recv_multipart()
            msg_type = msg[1]
            if msg_type == TASK:
#                print("Node: TASK from {0}".format(msg[0]))
                returnAddress = msg[0]
                task = msg[2]
                if available_workers > 0:
                    available_workers -= 1
                    address = workers_list.pop()
#                    print("removed: ", workers_list)
                    taskSocket.send_multipart([address, "TASK", task])
                else:
                    unassigned_tasks.append(task)
                
            elif msg_type == REQUEST:
#                print("Node: REQUEST from {0}".format(msg[0]))
                try:
                    address = msg[0]
                    task = unassigned_tasks.pop()
                    taskSocket.send_multipart([address, "TASK", task])
                except:
                    available_workers += 1
                    workers_list.append(msg[0])
#                    print("added: ", workers_list)
            elif msg_type == REPLY:
#                print("Node: REPLY from {0} to {1}".format(msg[0],msg[3]))
                address = msg[3]
                task = msg[2]
                taskSocket.send_multipart([address, "REPLY", task])
               
            elif msg_type == "SHUTDOWN":
                break

    infoSocket.send("SHUTDOWN")
    #out of infinite loop: do some housekeeping
    time.sleep (0.3)
    
    taskSocket.close()
    infoSocket.close()
    context.term()
