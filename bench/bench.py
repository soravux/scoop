import subprocess
import time
import os
import matplotlib.pyplot as plt

def main():
    benchmark = {'scoop-evosn.py': [],
                 'multiprocessing-evosn.py': [],
                 'serial-evosn.py': [],
                 'dtm-evosn.py': []}
    test_range = range(8, 15)
    bak_environ = os.environ.copy()
    for size in test_range:
        for file in benchmark.keys():
            print("Begin %s (%s)" % (file, size))
            if file == "scoop-evosn.py":
                begin_ts = time.time()
                child = subprocess.call(["python","scooprun.py","-N 2", file, str(size)], stdout=None, stdin=None)
                benchmark[file].append(time.time() - begin_ts)
            elif file == "multiprocessing-evosn.py" or file == "serial-evosn.py":
                begin_ts = time.time()
                child = subprocess.call(["python",file, str(size)], stdout=None, stdin=None)
                benchmark[file].append(time.time() - begin_ts)
            elif file == "dtm-evosn.py":
                begin_ts = time.time()
                child = subprocess.call(["mpirun","-n", "2", "python",  file, str(size)], stdout=None, stdin=None)
                benchmark[file].append(time.time() - begin_ts)
    print("results: ", benchmark)
    plt.figure()
    for a in benchmark.keys():
        plt.plot(test_range, benchmark[a], linewidth=1.0, marker='o', label=a)
    #plt.plot(test_range, benchmark['deaptest.py'], linewidth=1.0, marker='o', label="SCOOP")
    #plt.plot(test_range, benchmark['evosn.py'], linewidth=1.0, marker='o', label="Serial")
    plt.xlabel('size (N)')
    plt.ylabel('time (s)')
    plt.title('DEAP sorting network example')
    plt.legend()
    plt.savefig('bench.svg')
    plt.savefig('bench.pdf')


if __name__ == '__main__':
    main()
