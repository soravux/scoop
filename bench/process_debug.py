from __future__ import print_function
import sys
from collections import OrderedDict, namedtuple, defaultdict
import itertools
import time
import os
from datetime import datetime
import argparse
import pickle

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.dates import DateFormatter, MinuteLocator, SecondLocator
import numpy as np



DENSITY_MAP_TIME_AXIS_LENGTH = 800

TaskId = namedtuple('TaskId', ['worker', 'rank'])
FutureId = namedtuple('FutureId', ['worker', 'rank'])

parser = argparse.ArgumentParser(description='Analyse the debug info')
parser.add_argument("--inputdir", help='The directory containing the debug info',
        default="debug")

parser.add_argument("--prog", choices=["all", "broker", "density", "queue",
                                       "time", "task", "timeline"],
                    nargs='*', default=["all"], help="The output graph")

parser.add_argument("--output", help="The filename for the output graphs",
        default="debug.png")


args = parser.parse_args()


def getWorkersName(data):
    """Returns the list of the names of the workers sorted alphabetically"""
    names = [fichier for fichier in data.keys()]
    names.sort()
    try:
        names.remove("broker")
    except ValueError:
        pass
    return names

def importData(directory):
    """Parse the input files and return two dictionnaries"""
    dataTask = OrderedDict()
    dataQueue = OrderedDict()
    for fichier in os.listdir(directory):
        try:
            with open("{directory}/{fichier}".format(**locals()), 'rb') as f:
                fileName, fileType = fichier.rsplit('-', 1)
                if fileType == "QUEUE":
                    dataQueue[fileName] = pickle.load(f)
                else:
                    dataTask[fileName] = pickle.load(f)
        except:
            # Can be a directory
            pass
    return dataTask, dataQueue

def stepSize(startTime, endTime, points):
    step = int((endTime - startTime)/points)
    if step == 0:
        return 1
    else:
        return step

def timeRange(startTime, endTime, points):
    return range(int(startTime), int(endTime), stepSize(startTime, endTime,
        points))

def getTimes(dataTasks):
    """Get the start time and the end time of data in milliseconds"""
    start_time, end_time = float('inf'), 0
    for fichier, vals in dataTask.items():
        try:
            if hasattr(vals, 'values'):
                tmp_start_time = min([a['start_time'] for a in vals.values()])[0]
                if tmp_start_time < start_time:
                    start_time = tmp_start_time
                tmp_end_time = max([a['end_time'] for a in vals.values()])[0]
                if tmp_end_time > end_time:
                    end_time = tmp_end_time
        except ValueError:
            continue
    return 1000 * start_time, 1000 * end_time

def WorkersDensity(dataTasks):
    """Return the worker density data for the graph."""

    start_time, end_time = getTimes(dataTasks)
    graphdata = []

    for name in getWorkersName(dataTasks):
        vals = dataTasks[name]
        if hasattr(vals, 'values'):
            # Data from worker
            workerdata = []
            print("Plotting density map for {}".format(name))
            # We only have 800 pixels
            for graphtime in timeRange(start_time, end_time, DENSITY_MAP_TIME_AXIS_LENGTH):
                workerdata.append(sum([a['start_time'][0] <= float(graphtime) /
                    1000. <= a['end_time'][0] for a in vals.values()]))
            graphdata.append(workerdata)

            # Normalize [...]
            #maxval = max(graphdata[-1])
            #if maxval > 1:
            #    maxval = maxval - 1
            #    graphdata[-1] = [x - maxval for x in graphdata[-1]]
    return graphdata

def plotDensity(dataTask, filename):
    """Plot the worker density graph"""

    #def format_worker(x, pos=None):
    #    """Formats the worker name"""
    #    #workers = filter (lambda a: a[:6] != "broker", dataTask.keys())
    #    workers = [a for a in dataTask.keys() if a[:6] != "broker"]
    #    return workers[x]

    def format_time(x, pos=None):
        """Formats the time"""
        start_time, end_time = [a / 1000 for a in getTimes(dataTask)]
        ts = datetime.fromtimestamp((end_time - start_time) /
            DENSITY_MAP_TIME_AXIS_LENGTH * x + start_time)
        return ts.strftime("%H:%M:%S")

    graphdata = WorkersDensity(dataTask)
    if len(graphdata):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        box = ax.get_position()
        ax.set_position([box.x0 + 0.15 * box.width, box.y0, box.width, box.height])
        #cax = ax.imshow(graphdata, interpolation='nearest', aspect='auto')
        cax = ax.imshow(graphdata, interpolation='nearest', aspect='auto', cmap='RdYlGn')
        ax.grid(True, linewidth=2, color="w")
        plt.xlabel('time (s)'); plt.ylabel('Worker'); ax.set_title('Work density')
        ax.yaxis.set_ticks(range(len(graphdata)))
        ax.tick_params(axis='y', which='major', labelsize=6)
        #ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_worker))
        interval_size = DENSITY_MAP_TIME_AXIS_LENGTH // 4
        ax.xaxis.set_ticks(range(0,
                                 DENSITY_MAP_TIME_AXIS_LENGTH + interval_size,
                                 interval_size))
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_time))
        #cax.set_clim(0, 1)
        cbar = fig.colorbar(cax)#, ticks=[0, 1])
        fig.savefig(filename)

def plotBrokerQueue(dataTask, filename):
    """Generates the broker queue length graphic."""
    print("Plotting broker queue length for {0}.".format(filename))
    plt.figure()

    # Queue length
    plt.subplot(211)
    for fichier, vals in dataTask.items():
        if type(vals) == list:
            timestamps = list(map(datetime.fromtimestamp, map(int, list(zip(*vals))[0])))
            # Data is from broker
            plt.plot_date(timestamps, list(zip(*vals))[2],
                          linewidth=1.0,
                          marker='o',
                          markersize=2,
                          label=fichier)
    plt.title('Broker queue length')
    plt.ylabel('Tasks')

    # Requests received
    plt.subplot(212)
    for fichier, vals in dataTask.items():
        if type(vals) == list:
            timestamps = list(map(datetime.fromtimestamp, map(int, list(zip(*vals))[0])))
            # Data is from broker
            plt.plot_date(timestamps, list(zip(*vals))[3],
                          linewidth=1.0,
                          marker='o',
                          markersize=2,
                          label=fichier)
    plt.title('Broker pending requests')
    plt.xlabel('time (s)')
    plt.ylabel('Requests')

    plt.savefig(filename)

def plotWorkerQueue(dataQueue, filename):
    # workers Queue length Graph
    fig = plt.figure()
    ax = fig.add_subplot(111)

    x = []
    for a, b in dataQueue.items():
        nb = []
        for bb in b:
            if bb == float('inf'):
                nb.append(1)
            else:
                nb.append(bb)
        x.append([a, nb])
    dataQueue = x

    for fichier, vals in dataQueue:
        print("Plotting {}".format(fichier))
        ax.plot(*(list(zip(*vals))[:2]), label=fichier)
    plt.xlabel('time(s)'); plt.ylabel('Queue Length')
    plt.title('Queue length through time')
    fig.savefig(filename)

def getWorkerInfo(dataTask):
    """Returns the total execution time and task quantity by worker"""
    workertime = []
    workertasks = []
    for fichier, vals in dataTask.items():
        if hasattr(vals, 'values'):
            #workers_names.append(fichier)
            # Data from worker
            totaltime = sum([a['executionTime'] for a in vals.values()])
            totaltasks = sum([1 for a in vals.values()])
            workertime.append(totaltime)
            workertasks.append(totaltasks)
    return workertime, workertasks

def plotWorkerTime(workertime, worker_names, filename):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ind = range(len(workertime))
    width = 1

    rects = ax.bar(ind, workertime, width, edgecolor="black")
    ax.set_ylabel('Time (s)')
    ax.set_title('Effective execution time by worker')
    #ax.set_xticks([x+(width/2.0) for x in ind])
    ax.set_xlabel('Worker')
    #ax.tick_params(axis='x', which='major', labelsize=6)
    #ax.set_xticklabels(worker_names)
    ax.set_xlim([-1, len(worker_names) + 1])
    ax.set_xticklabels([])
    

    fig.savefig(filename)


def plotWorkerTask(workertask, worker_names, filename):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ind = range(len(workertask))
    width = 1

    rects = ax.bar(ind, workertask, width, edgecolor="black")
    ax.set_ylabel('Tasks')
    ax.set_title('Number of tasks executed by worker')
    #ax.set_xticks([x+(width/2.0) for x in ind])
    ax.set_xlabel('Worker')
    #ax.tick_params(axis='x', which='major', labelsize=6)
    ax.set_xticklabels([])
    ax.set_xlim([-1, len(worker_names) + 1])
    #ax.set_xticklabels(range(len(worker_names)))

    fig.savefig(filename)


def timelines(fig, y, xstart, xstop, color='b'):
    """Plot timelines at y from xstart to xstop with given color."""
    fig.hlines(y, xstart, xstop, color, lw=4)
    fig.vlines(xstart, y+0.03, y-0.03, color, lw=2)
    fig.vlines(xstop, y+0.03, y-0.03, color, lw=2)


def plotTimeline(dataTask, filename):
    """Build a timeline"""

    fig = plt.figure()
    ax = fig.gca()

    worker_names = [x for x in dataTask.keys() if "broker" not in x]

    times = []
    for worker, vals in dataTask.items():
        if hasattr(vals, 'values'):
            for future in vals.values():
                times.append(future['start_time'][0])
    try:
        min_time = min(times)
    except:
        min_time = 0
    ystep = 1. / (len(worker_names) + 1)

    y = 0
    for worker, vals in dataTask.items():
        if "broker" in worker:
            continue
        y += ystep
        if hasattr(vals, 'values'):
            for future in vals.values():
                start_time = [future['start_time'][0] - min_time]
                end_time = [future['end_time'][0] - min_time]
                timelines(ax, y, start_time, end_time)


    #ax.xaxis_date()
    #myFmt = DateFormatter('%H:%M:%S')
    #ax.xaxis.set_major_formatter(myFmt)
    #ax.xaxis.set_major_locator(SecondLocator(0, interval=20))

    #delta = (stop.max() - start.min())/10
    ax.set_yticks(np.arange(ystep, 1, ystep))
    ax.set_yticklabels(worker_names)
    ax.set_ylim(0, 1)
    #fig.xlim()
    ax.set_xlabel('Time')
    fig.savefig(filename)


if __name__ == "__main__":
    dataTask, dataQueue = importData(args.inputdir)

    if any(prog in ["density", "all"] for prog in args.prog):
        plotDensity(dataTask, "density_" + args.output)

    if any(prog in ["broker", "all"] for prog in args.prog):
        plotBrokerQueue(dataTask, "broker_" + args.output)

    if any(prog in ["queue", "all"] for prog in args.prog):
        plotWorkerQueue(dataQueue, "queue_" + args.output)

    if any(prog in ["time", "all"] for prog in args.prog):
        workerTime, workerTasks = getWorkerInfo(dataTask)
        plotWorkerTime(workerTime, getWorkersName(dataTask), "time_" + args.output)

    if any(prog in ["task", "all"] for prog in args.prog):
        workerTime, workerTasks = getWorkerInfo(dataTask)
        plotWorkerTask(workerTasks, getWorkersName(dataTask), "task_" + args.output)

    if any(prog in ["timeline", "all"] for prog in args.prog):
        plotTimeline(dataTask, "timeline_" + args.output)
