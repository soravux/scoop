# -*- coding: utf-8 -*-
# <nbformat>2</nbformat>

# <markdowncell>

# To do the benchmark and use this file to parse the result, you must use the following instructions.
# 
# The tests are parsed using the following command:    
# usr/bin/time -o filename.txt -a --format="%C;%e" scooprun.py -N 1 evosn.py
# 
# or
# 
# usr/bin/time -o filename.txt -a --format="%C;%e" mpirun -N 1 python evosn.py
# 
# You must use a different file for each library you wan't to benchmark.
# 
# The variable you wan't to control must be given in the argument variable bellow. The sintax is ("Command line variable", "Real name of the variable").
# 
# You must add the names of the tests in the tests dictionary along with the name of the file that contains the benchmark results.
# 
# If you wan't to compare the benchmark with the serial benchmark, you must put the serial time in the "SERIAL_TIME" variable. If not, you must put None.
# 
# The "TEST_NAME" variable is used for the graph titles.

# <codecell>

from __future__ import print_function
from matplotlib import pyplot as plt

# <markdowncell>

# This section defines the arguments of the parser.

# <codecell>

ARGUMENT = ("-n", "Cores")
TESTS = {"scoop":"scooptimes.txt", "dtm":"dtmtimes.txt"}
TEST_NAME = "local"
SERIAL_TIME = 179.57 # keep None if you wan't speedup graph to measure against themselve.

# <codecell>

def getData(filename, argument):
    f = open(filename, 'r')
    times = []
    for line in f.readlines():
        line = line.strip("\n")
        times.append(line.split(";"))
    f.close()
    times = zip(*times)
    command = times[0]
    times = times[1]
    command = [comm.split() for comm in command]
    
    # we search the value of the argument
    cores = [float(comm[comm.index(argument) + 1]) for comm in command]
    times = [float(time) for time in times]
    
    # we sort the variables for the graphs
    l = zip(cores,times)
    l.sort()
    return [c for c, t in l], [t for c, t in l]

# <markdowncell>

# Now we graph the times obtained in the precedent section of code.

# <codecell>

for test in TESTS.keys():
    cores, times = getData(TESTS[test], ARGUMENT[0])
    plt.plot(cores, times, label=test, linewidth=1.0, marker='o')
plt.title("times on {0}".format(TEST_NAME))
plt.xlabel(ARGUMENT[1])
plt.ylabel("time (s)")
plt.legend()
plt.savefig("{0}_speed.png".format(TEST_NAME))
try:
    display()
except:
    plt.show()
    
plt.figure()
for test in TESTS.keys():
    cores, times = getData(TESTS[test], ARGUMENT[0])
    if SERIAL_TIME == None:
        serial_time = times[0]
    else:
        serial_time = SERIAL_TIME
    speedup = [serial_time/time for time in times]
    plt.plot(cores, speedup, label=test, linewidth=1.0, marker='o')
plt.title("times on {0}".format(TEST_NAME))
plt.xlabel(ARGUMENT[1])
plt.ylabel("time (s)")
plt.legend(loc=2)
plt.savefig("{0}_speed.png".format(TEST_NAME))
try:
    display()
except:
    plt.show()

