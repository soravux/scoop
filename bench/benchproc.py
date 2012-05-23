from __future__ import print_function
import subprocess
import time
import os
import matplotlib.pyplot as plt
import argparse


# to change the file to benchmark, change the string in filename
filename = "tree"
filepath = "tree/"
cores    = 2 # maximum number of cores on the computer

def main():
    serial_benchmark = None
    print("Begin serial benchmark")
    begin_ts = time.time()
    child = subprocess.call(["python",
                             "{1}serial-{0}.py".format(filename, filepath),
                             "12"],
                             stdout=None, stdin=None)
    serial_benchmark = time.time() - begin_ts

    print("serial benchmark:{0}".format(serial_benchmark))

    benchmark = {'scoop-{0}.py'.format(filename): [],
                 #'multiprocessing-{0}.py'.format(filename): [],
                 'dtm-{0}.py'.format(filename): []}
    test_range = range(1, cores + 1)
    for n in test_range:
        for file in benchmark.keys():
            print("Begin %s (%s)" % (file, n))
            if file == "scoop-{0}.py".format(filename):
                begin_ts = time.time()

                # python scooprun -N n exec.py

                child = subprocess.call(["scooprun.py",
                                        "-vvv","-N {0}".format(n),
                                        filepath+file],
                                        stdout=None, stdin=None)
                benchmark[file].append(serial_benchmark/(time.time() - begin_ts))


            elif file == "multiprocessing-{0}.py".format(filename):

                begin_ts = time.time()

                # python exec.py -N n
                # To use this benchmark, we must be able to change the number of
                # process by using the option -N n.

                child = subprocess.call(["python",
                                         filepath + file,
                                         "12",
                                         str(n)],
                                         stdout=None, stdin=None)
                benchmark[file].append(serial_benchmark/(time.time() - begin_ts))


            elif file == "dtm-{0}.py".format(filename):
                begin_ts = time.time()

                # mpirun -n n python exec.py

                child = subprocess.call(["mpirun",
                                         "-n", str(n),
                                         "python",
                                         filepath + file],
                                         stdout=None, stdin=None)
                benchmark[file].append(serial_benchmark/(time.time() - begin_ts))

    print("results: ", benchmark)
    plt.figure()
    for a in benchmark.keys():
        plt.plot(test_range, benchmark[a], linewidth=1.0, marker='o', label=a)
    plt.xlabel('cores (N)')
    plt.ylabel('time (s)')
    plt.title('speedup benchmark')
    plt.legend()
    plt.savefig('benchCores.svg')
    plt.savefig('benchCores.pdf')


if __name__ == '__main__':
    main()
