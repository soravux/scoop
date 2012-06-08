from __future__ import print_function
import sys
from collections import OrderedDict, namedtuple
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import itertools
import os

TaskId = namedtuple('TaskId', ['worker', 'rank'])
FutureId = namedtuple('FutureId', ['worker', 'rank'])

dataTask = OrderedDict()
dataQueue = {}

def format_worker(x, pos=None):
    """This function is used as a formater"""
    return dataTask.keys()[x]

# Parse the input files
for fichier in os.listdir("debug"):
    print("opening {}".format(fichier))
    with open("debug/"+fichier, 'r') as f:
        splitFile = fichier.split('-')
        fileType = splitFile[1]
        fileName = splitFile[0]
        if  fileType == "QUEUE":
            dataQueue[fileName] = eval(f.read())
        else:
            dataTask[fileName] = eval(f.read())

print(dataQueue)

# First graph
graphdata = []
workers_names = []
# Get start and end times 
start_time = 9999999999999999999999999; end_time = 0
for fichier, vals in dataTask.items():
    if type(vals) == dict:
        tmp_start_time = min([a['start_time'] for a in vals.values()])[0]
        if tmp_start_time < start_time:
            start_time = tmp_start_time
        tmp_end_time = max([a['end_time'] for a in vals.values()])[0]
        if tmp_end_time > end_time:
            end_time = tmp_end_time

# We determine the step size for the graphs.

step = (end_time - start_time)/2000
if step < 100:
    step = 100
print("range {0} step {1}".format(end_time - start_time, step))

for fichier, vals in dataTask.items():
    if type(vals) == dict:
        workers_names.append(fichier)
        # Data from worker
        workerdata = []
        print(fichier)
        for graphtime in range(int(start_time * 100.), int(end_time * 100.),
                int(step*100.)):
            workerdata.append(sum([a['start_time'][0] <= float(graphtime) / 100. <= a['end_time'][0] for a in vals.values()]))
        graphdata.append(workerdata)
fig = plt.figure()
ax = fig.add_subplot(111)
box = ax.get_position()
ax.set_position([box.x0 + 0.15 * box.width, box.y0, box.width, box.height])
cax = ax.imshow(graphdata, interpolation='nearest', aspect='auto')
plt.xlabel('time (ms)'); plt.ylabel('Queue Length'); ax.set_title('Work density')
ax.yaxis.set_ticks(range(len(graphdata)))
ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_worker))
cbar = fig.colorbar(cax)
fig.savefig('WorkerDensity.png')

# Broker Queue length Graph
fig = plt.figure()
ax = fig.add_subplot(111)
for fichier, vals in dataTask.items():
    if type(vals) == list:
        # Data is from broker
        ax.plot(zip(*vals)[0], zip(*vals)[2], linewidth=1.0, marker='o', label=fichier)
plt.xlabel('time (s)'); plt.ylabel('Entries in broker queue')
plt.title('Evolution of broker queue size during the job')
box = ax.get_position()
ax.set_position([box.x0, box.y0, box.width * 0.80, box.height])
ax.legend(loc='center left', bbox_to_anchor=(1.00, 0.5))
plt.setp(plt.gca().get_legend().get_texts(), fontsize='small')
fig.savefig('BrokerQueueLength.png')

# Broker Queue length Graph
fig = plt.figure()
ax = fig.add_subplot(111)
for fichier, vals in dataTask.items():
    if type(vals) == list:
        # Data is from broker
        ax.plot(zip(*vals)[0], zip(*vals)[3], linewidth=1.0, marker='o', label=fichier)
plt.xlabel('time (s)'); plt.ylabel('Available workers')
plt.title('Evolution of awaiting workers during the job')
box = ax.get_position()
ax.set_position([box.x0, box.y0, box.width * 0.80, box.height])
ax.legend(loc='center left', bbox_to_anchor=(1.00, 0.5))
plt.setp(plt.gca().get_legend().get_texts(), fontsize='small')
fig.savefig('BrokerAwaitingWorkers.png')


# workers Queue length Graph
fig = plt.figure()
ax = fig.add_subplot(111)

for fichier, vals in dataQueue.items():
    print(zip(*vals))
    ax.plot(*zip(*vals), label=fichier)
    print("plotted")
plt.xlabel('time(s)'); plt.ylabel('Queue Length')
plt.title('Queue length throught time')
ax.legend(loc='center left')
fig.savefig('QueueLength.png')

