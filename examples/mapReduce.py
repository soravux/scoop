from scoop import futures
import operator
import time

def abc(indata):
    # Simulate a 10ms workload on every tasks
    time.sleep(0.01)
    return sum(indata)

if __name__ == '__main__':
    scoopTime = time.time()
    res = futures.mapReduce(abc, operator.add, list([a] * a for a in range(1000)))
    scoopTime = time.time() - scoopTime
    print("Executed parallely in: {0:.3f}s with result: {1}".format(
        scoopTime,
        res
        )
    )

    serialTime = time.time()
    res = sum(map(abc, list([a] * a for a in range(1000))))
    serialTime = time.time() - serialTime
    print("Executed serially in: {0:.3f}s with result: {1}".format(
        serialTime,
        res
        )
    )