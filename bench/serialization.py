import pickle
import time
import numpy
import random
from scipy import stats

TRIES = 500
DATA_SIZE = [2 ** i for i in range(12)]

def find_pickling_speed(tries, data_size):
    results_pickling = []
    results_unpickling = []
    data_size = [2 ** i for i in range(data_size)]
    for size in data_size:
        data = [[random.random() for _ in range(size)] for _ in range(tries)]
        pickeled_data = []
        start_time = time.time()
        for d in data:
            pickeled_data.append(pickle.dumps(d))

        end_time = time.time()

        results_pickling.append((end_time - start_time)/tries)


    slope, _, _, _, _ = stats.linregress(data_size, results_pickling)

    return slope

if __name__ == "__main__":
    import pylab as plt
    print("Serialization test")
    results_pickling = []
    results_unpickling = []
    for size in DATA_SIZE:
        print("Starting size {}".format(size))
        data = [[random.random() for _ in range(size)] for _ in range(TRIES)]
        pickeled_data = []
        start_time = time.time()
        for d in data:
            pickeled_data.append(pickle.dumps(d))

        end_time = time.time()

        results_pickling.append((end_time - start_time)/TRIES)

        start_time = time.time()
        for pd in pickeled_data:
            x = pickle.loads(pd)
        end_time = time.time()

        results_unpickling.append((end_time - start_time)/TRIES)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(DATA_SIZE, results_pickling, label = "pickling")
    ax.plot(DATA_SIZE, results_unpickling, label = "unpickling")

    ax.set_xlabel('Number of floats')
    ax.set_ylabel('time (s)')
    ax.set_title('Pickling time')

    leg = ax.legend()

    slope, intercept, _, _, std_err = stats.linregress(DATA_SIZE, results_pickling)
    print("La fonction linéaire du temps de pickling est:")
    print( "{} * x + {} = t".format(slope, intercept))
    print("x est le nombre de float écrit et t est le temps en secondes")

    slope, intercept, _, _, std_err = stats.linregress(DATA_SIZE, results_unpickling)
    print("La fonction linéaire du temps de unpickling est:")
    print( "{} * x + {} = t".format(slope, intercept))
    print("x est le nombre de float écrit et t est le temps en secondes")

    import sys
    print(("Ce test a été effectué avec cette version de Cpython: \n{}"
           "\nIl a été effectué sur une plateforme {}.").format(sys.version,
                                                                sys.platform))

    plt.show()
