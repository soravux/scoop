# Small Scale #

Here are the specifications of the computer used for small-scale benchmarks:
  * Intel(R) Core(TM) i7 CPU 920 @ 2.67GHz
  * Python 2.7.3
  * Linux 2.6.32-21-generic x86\_64
  * SCOOP [r273](https://code.google.com/p/scoop/source/detail?r=273)

The benchmarks shows the speedup of different typical problems and compares [DTM](https://code.google.com/p/deap/#DTM) to SCOOP.

## Unbalanced Tree ##

This test used the `examples/tree` system to generate an unbalanced tree having these statistics:
  * Height : 5
  * Leaves : 333
  * Nodes : 457
  * Average node execution time : 1s

![https://docs.google.com/spreadsheet/oimg?key=0Ap8EkU7GB3scdFZqZ0FHVEZTNExHYXZkTmdxMG9GNlE&oid=2&zx=7rt7iumpmz47&.png](https://docs.google.com/spreadsheet/oimg?key=0Ap8EkU7GB3scdFZqZ0FHVEZTNExHYXZkTmdxMG9GNlE&oid=2&zx=7rt7iumpmz47&.png)

## Genetic Algorithms - Sorting network evolution ##

The following benchmark uses the [DEAP](http://deap.googlecode.com/) software to execute genetic algorithms.

![https://docs.google.com/spreadsheet/oimg?key=0AvvJsDb3Es26dDNGeF8xd2R1WVhPVzBRbUQxYU9rN2c&oid=12&zx=xq8bpoin4yxg&.png](https://docs.google.com/spreadsheet/oimg?key=0AvvJsDb3Es26dDNGeF8xd2R1WVhPVzBRbUQxYU9rN2c&oid=12&zx=xq8bpoin4yxg&.png)

# Medium Scale #

These benchmarks have been executed on the [Colosse](http://www.clumeq.ca/index.php/en/about/computers/colossus), [Guillimin](http://www.clumeq.ca/index.php/en/support/144-quelles-sont-les-specifications-de-guillimin), [Mamouth-MP2](https://rqchp.ca/?mod=cms&pageId=1388&lang=EN) and [Briarée](https://rqchp.ca/?mod=cms&pageId=1327&lang=EN) supercomputers.

They use Python 2.7.3.

## Genetic Algorithms - Sorting network evolution ##

The following benchmark uses the [DEAP](http://deap.googlecode.com/) software to execute genetic algorithms.

![https://docs.google.com/spreadsheet/oimg?key=0AvvJsDb3Es26dDNGeF8xd2R1WVhPVzBRbUQxYU9rN2c&oid=13&zx=2jjeoz9htr4c&.png](https://docs.google.com/spreadsheet/oimg?key=0AvvJsDb3Es26dDNGeF8xd2R1WVhPVzBRbUQxYU9rN2c&oid=13&zx=2jjeoz9htr4c&.png)

# Load Balancing #

The following graphic shows the result of a typical load balancing. This data was obtained using the evolutionary algorithm example. This example spawns multiple tasks using a single [map](http://scoop.readthedocs.org/en/latest/api.html#scoop.futures.map).

Between each generations, a serial section is executed (the mutation and crossover), explaining the vertical bars without work on the remote workers. This is a non-parallelized section of the code, hence not related to SCOOP. The first worker is shown as executing two tasks because the user program execution takes place on it.

![http://benchmarks.scoop.googlecode.com/hg/pub/loadBalancing.png](http://benchmarks.scoop.googlecode.com/hg/pub/loadBalancing.png)