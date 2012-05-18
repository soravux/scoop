How to use SCOOP on a grid
==========================

Environment setup
-----------------

Here is a scratchpad allowing you to set a minimal local python environment without the need to be administrator on a Linux system::

    [~]$ mkdir downloads && cd downloads/
    [downloads]$ wget http://www.python.org/ftp/python/2.7.3/Python-2.7.3.tar.bz2
    [downloads]$ tar xfvj Python-2.7.3.tar.bz2 && cd Python-2.7.3
    [Python-2.7.3]$ ./configure --prefix=$HOME/python && make && make install
    [Python-2.7.3]$ export PATH=$HOME/python/bin:$PATH && echo "You should put this line in your .bashrc for persistency."
    [Python-2.7.3]$ cd ..
    [downloads]$ wget --no-check-certificate http://python-distribute.org/distribute_setup.py
    [downloads]$ python distribute_setup.py
    [downloads]$ wget --no-check-certificate  https://raw.github.com/pypa/pip/master/contrib/get-pip.py
    [downloads]$ python get-pip.py
    [downloads]$ pip install -U greenlet==dev
    [downloads]$ wget http://download.zeromq.org/zeromq-2.2.0.tar.gz
    [downloads]$ tar xfvz zeromq-2.2.0.tar.gz && cd zeromq-2.2.0
    [zeromq-2.2.0]$ ./configure --prefix=$HOME/zmq/ && make && make install
    [zeromq-2.2.0]$ export PATH=$PATH:$HOME/zmq/lib
    [zeromq-2.2.0]$ cd ..
    [downloads]$ wget --no-check-certificate https://github.com/downloads/zeromq/pyzmq/pyzmq-2.2.0.tar.gz
    [downloads]$ tar xfvz pyzmq-2.2.0.tar.gz && cd pyzmq-2.2.0
    [pyzmq-2.2.0]$ python setup.py configure --zmq=$HOME/zmq && python setup.py install
    [pyzmq-2.2.0]$ cd ..
    [downloads]$ pip install mercurial
    [downloads]$ hg clone https://code.google.com/p/scoop/ ./scoop/
    [downloads]$ cd scoop/
    [downloads]$ python setup.py install
    [examples]$ mkdir ~/.ssh && cd ~/.ssh
    [.ssh]$ ssh-keygen -t dsa
    [.ssh]$ cat id_dsa.pub >> authorized_keys2
    [.ssh]$ cd $HOME/downloads/scoop/examples/


Startup scripts
---------------

On grids, you must provide startup scripts to the task scheduler. Here is provided some example startup scripts using different grid task managers.

.. note::

    **Please note that these are only examples**. Refer to the documentation of your own scheduler to get the list of every arguments you must and/or can pass to be able the run the task on your grid.

Moab & Torque
~~~~~~~~~~~~~

Here is an example of submit file for Torque::

    #!/bin/bash
    #PBS -l procs=4
    #PBS -o out
    #PBS -e err
    #PBS -V
    #PBS -q debug
    #PBS -N ScoopTesting

    # Path to your executable. For example, if you extracted SCOOP to $HOME/downloads/scoop
    cd $HOME/downloads/scoop/examples

    # Add any addition to your environment variables like PATH. For example, if your local python installation is in $HOME/python
    export PATH=$HOME/python/bin:$PATH
    
    # If, instead, you are using the python offered by the system, you can stipulate it's library path via PYTHONPATH
    #export PYTHONPATH=$HOME/wanted/path/lib/python+version/site-packages/:$PYTHONPATH

    # Torque set the list of nodes allocated to our task in a file referenced by the environment variable PBS_NODEFILE.
    hosts=$(cat $PBS_NODEFILE | sed ':a;N;$!ba;s/\n/ /g')
    
    # Launch SCOOP using the hosts
    time scooprun.py --hosts $hosts -vv -N 4 fullTree.py --python-executable `which python` -b


Sun Grid Engine (SGE)
~~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for SGE::

    #$ -l h_rt=300
    #$ -pe test 16
    #$ -S /bin/bash
    #$ -cwd
    #$ -notify
    
    # Path to your executable. For example, if you extracted SCOOP to $HOME/downloads/scoop
    cd $HOME/downloads/scoop/examples
    
    # Add any addition to your environment variables like PATH. For example, if your local python installation is in $HOME/python
    export PATH=$HOME/python/bin:$PATH
    
    # If, instead, you are using the python offered by the system, you can stipulate it's library path via PYTHONPATH
    #export PYTHONPATH=$HOME/wanted/path/lib/python+version/site-packages/:$PYTHONPATH

    # Get a list of the (routable name) hosts assigned to our task
    hosts=$(cat $PE_HOSTFILE | awk '{printf "%s ", $1}')

    # Launch the remotes workers
    time scooprun.py --hosts $hosts -vv -N 16 test-scoop.py --python-executable `which python` -b
    
.. note::
    
    If you are using the python offered by the system, you can still install the dependencies with the ``--prefix`` argument::
    
        python setup.py install --prefix=$HOME/wanted/path/
    
    You will then be able to include these libraries by modifying the example startup scripts like this::
    
        #export PATH=$HOME/python/bin:$PATH
        export PYTHONPATH=$HOME/wanted/path/lib/python+version/site-packages/:$PYTHONPATH