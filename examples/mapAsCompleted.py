from scoop import futures

def hello(input):
    return input

if __name__ == "__main__":
    for out in futures.map(hello, range(10)):
        print("Hello from #{}!".format(out))

    for out in futures.map_as_completed(hello, range(10)):
        print("Hello from #{}!".format(out))
