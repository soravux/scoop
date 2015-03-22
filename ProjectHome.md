![http://scoop.readthedocs.org/en/latest/_images/logo.png](http://scoop.readthedocs.org/en/latest/_images/logo.png)

SCOOP (Scalable COncurrent Operations in Python) is a distributed task
module allowing concurrent parallel programming on various environments,
from heterogeneous grids to supercomputers. Its documentation is available on [scoop.readthedocs.org](http://scoop.readthedocs.org/).

# Philosophy #

SCOOP was designed from the following ideas:

  * The future is parallel;
  * Simple is beautiful;
  * Parallelism should be simpler.

These tenets are translated concretely in a minimum number of functions
allowing maximum parallel efficiency while keeping at minimum the
inner knowledge required to use them. It is implemented with Python 3 in mind
while being compatible with Python 2.6+ to allow fast prototyping without sacrificing
efficiency and speed.

Some comments we received on SCOOP:

  * "I must say that that was by far the easiest upgrade I have probably ever done.  I still need to build and test it on the cluster, but on my development machine it took about 10 minutes to upgrade and test." [EBo, deap Mailing list](https://groups.google.com/d/msg/deap-users/chQY-2HHZWM/4qZRkQuvbbIJ)

# Features #

SCOOP features and advantages over
[futures](http://docs.python.org/dev/library/concurrent.futures.html),
[multiprocessing](http://docs.python.org/dev/library/multiprocessing.html)
and similar modules are as follows:

  * Harness the power of multiple computers over network;
  * Ability to spawn multiple tasks inside a task;
  * API compatible with [PEP-3148](http://www.python.org/dev/peps/pep-3148/);
  * Parallelizing serial code with only minor modifications;
  * Efficient load-balancing.

## Anatomy of a SCOOPed program ##

SCOOP can handle multiple diversified multi-layered tasks. With it, you can submit your different functions and data simultaneously and effortlessly while the framework executes them locally or remotely. Contrarily to most multiprocessing frameworks, it allows to launch subtasks within tasks.

![http://scoop.readthedocs.org/en/latest/_images/introductory_tree.png](http://scoop.readthedocs.org/en/latest/_images/introductory_tree.png)

Through SCOOP, you can execute simultaneously tasks that are different by
nature, shown by the task color, or different by complexity, shown by the task radius. The module will handle the physical considerations of parallelization, such as task distribution over your resources (load balancing), communications, etc.

## Applications ##

The common applications of SCOOP consist but is not limited to:

  * Evolutionary Algorithms
  * Monte Carlo simulations
  * Data mining
  * Data processing
  * Graph traversal

# Citing SCOOP #

Authors of scientific papers including results generated using SCOOP are encouraged to cite the following paper.

```
@inproceedings{SCOOP_XSEDE2014,
  title={Once you SCOOP, no need to fork},
  author={Hold-Geoffroy, Yannick and Gagnon, Olivier and Parizeau, Marc},
  booktitle={Proceedings of the 2014 Annual Conference on Extreme Science and Engineering Discovery Environment},
  pages={60},
  year={2014},
  organization={ACM}
}
```

# Useful links #

You can [download the latest stable version](https://pypi.python.org/pypi/scoop/), check the project [documentation](http://scoop.readthedocs.org/), post to the [mailing list](http://groups.google.com/group/scoop-users) or [submit an issue](http://code.google.com/p/scoop/issues/list) if you've found one.