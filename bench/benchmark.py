import sys
import scoop
import time
import argparse
import logging
import random
from serialization import find_pickling_speed
from functools import partial

def make_parser():
    parser = argparse.ArgumentParser(description=('Run a parametric benchmark.'
                                                 'of scoop.'))

    parser.add_argument('--time', type = float, default = 5.0,
                        help = "The mean time of each individual task")

    parser.add_argument('--serialization-time', type = float, default = 0.01,
                        help = "The mean serialization time for each task")

    parser.add_argument('--tries', type = int, default = 10,
                        help = ("The number of functions sent to the workers "
                                "for each level of the hierchy"))

    parser.add_argument('--log', help = ("A filename to log the output "
                                        "(optional). This is different than the"
                                        'scoop "--log" option'))

    parser.add_argument('--level', help = "Number of level in the hierarchy",
                        type = int, default = 2)
    return parser

def print_header(args):
    header = ("-------------------------------------------------\n"
              "Benchmarking using these parameters:\n"
              "tries: {0.tries}^{0.level} = {1}\n"
              "time: {0.time} s\n"
              "serialization time: {0.serialization_time} s\n"
              "SCOOP Parameters:\n"
              "number of workers: {2} workers\n"
              "number of brokers: {3} brokers\n"
              "SCOOP version: {4}\n"
              "Python version {5}\n"
              "-------------------------------------------------\n")
    header = header.format(args, args.tries ** args.level,
            scoop.SIZE, 1, scoop.__version__ + scoop.__revision__,
            sys.version)
    if args.log:
        with open(args.log, 'a') as f:
            f.write(header)
    else:
        print(header)

def test_function(_fake_data, cpu_time = 3.0, level = 0, number_of_tests = 1):
    start_time = time.time()

    test_partial = partial(test_function, number_of_tests = number_of_tests,
                           level = level - 1, cpu_time = cpu_time)
    test_partial.__name__ = "test_partial"

    total = 0
    number_of_times = 0
    while time.time() - start_time < cpu_time:
        total += random.random()
        number_of_times += 1
    if level <= 1:
        if number_of_times != 0:
            return total / number_of_times
        else:
            return 0.5
    else:
        test_data = (_fake_data for _ in range(number_of_tests))
        children = scoop.futures.map(test_partial, test_data)
        return sum(children) / number_of_tests



def test(number_of_tests, cpu_time, serialization_time, log, levels):

    test_partial = partial(test_function, number_of_tests = number_of_tests,
                           level = levels, cpu_time = cpu_time)
    test_partial.__name__ = "test_partial"


    fake_data_len = find_serialization_time(serialization_time, log)
    fake_data = [random.random() for _ in range(fake_data_len)]
    send_data = (fake_data for _ in range(number_of_tests))
    begin_time = time.time()
    result = list(scoop.futures.map(test_partial, send_data))
    total_time = time.time() - begin_time
    return result, total_time

def find_serialization_time(wanted_time, log):
    speed = find_pickling_speed(500, 14)
    if log:
        with open(log, 'a') as f:
            f.write("The pickling speed is {:g} bytes/s.\n".format(1/speed))
    else:
        print("The pickling speed is {:g} bytes/s.".format(1/speed))
    return int(wanted_time / speed)

if __name__ == "__main__":
    args = make_parser().parse_args()
    print_header(args)

    start_time = time.time()

    result, test_time = test(args.tries, args.time,
                             args.serialization_time, args.log,
                             args.level)

    end_time = time.time()
    if args.log:
        with open(args.log, 'a') as f:
            f.write("Total time: {}\n".format(end_time - start_time))
            f.write("Test time: {}\n".format(test_time))
    else:
        print("Total time: {}".format(end_time - start_time))
        print("Test time: {}".format(test_time))


