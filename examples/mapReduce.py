from scoop import futures
import operator
import time

def manipulateData(inData):
    # Simulate a 10ms workload on every tasks
    time.sleep(0.01)
    return sum(inData)

if __name__ == '__main__':
    scoopTime = time.time()
    res = futures.mapReduce(manipulateData,
                            operator.add,
                            list([a] * a for a in range(1000))
                            )
    scoopTime = time.time() - scoopTime
    print("Executed parallely in: {0:.3f}s with result: {1}".format(
        scoopTime,
        res
        )
    )

    serialTime = time.time()
    res = sum(map(manipulateData, list([a] * a for a in range(1000))))
    serialTime = time.time() - serialTime
    print("Executed serially in: {0:.3f}s with result: {1}".format(
        serialTime,
        res
        )
    )