Setup
=====

Environment setup
-----------------

.. Soon : wget http://scoop.googlecode.com/hg/scoop_install.sh && chmod u+x scoop_install.sh && ./scoop_install.sh

Here is a scratchpad allowing you to set a working SCOOP environment.

Python environment
~~~~~~~~~~~~~~~~~~

Follow this **optional** section if you need to use another Python version (ie. 
3.2.3 in this example) than the system's::

    [~]$ mkdir downloads && cd downloads/
    [downloads]$ wget http://www.python.org/ftp/python/3.2.3/Python-3.2.3.tar.bz2
    [downloads]$ tar xfvj Python-3.2.3.tar.bz2 && cd Python-3.2.3
    [Python-3.2.3]$ ./configure --prefix=$HOME/python && make && make install
    [Python-3.2.3]$ export PATH=$HOME/python/bin:$PATH && echo "You should put this line in your .bashrc for persistency."
    [Python-3.2.3]$ cd ..
    [downloads]$ wget --no-check-certificate http://python-distribute.org/distribute_setup.py
    [downloads]$ python distribute_setup.py
    [downloads]$ wget --no-check-certificate  https://raw.github.com/pypa/pip/master/contrib/get-pip.py
    [downloads]$ python get-pip.py
    
.. note::
    
    If you are using the python offered by the system (the python which came 
    installed by your operating system) but can't install packages in the 
    system-wide library path, you can still install the dependencies with the 
    ``--prefix`` argument. See the `official documentation 
    <http://docs.python.org/install/index.html#alternate-installation>`_ about 
    alternate installation paths. It can be used as such::
    
        python setup.py install --prefix=$HOME/wanted/path/
    
    You will then be able to include these libraries by modifying the example 
    startup scripts like this::
    
        #export PATH=$HOME/python/bin:$PATH
        export PYTHONPATH=$HOME/wanted/path/lib/python+version/site-packages/:$PYTHONPATH
        
    Keep in mind that this technique is tedious since you must keep your 
    repository organised yourself and remember to use the ``--prefix`` argument.
    
    We **strongly** recommend that you use a 
    `virtualenv <http://pypi.python.org/pypi/virtualenv>`_ alongside with a 
    `wrapper <http://www.doughellmann.com/projects/virtualenvwrapper/>`_ instead of manually handling installation paths. Please check their documentations for more informations.

Requirements
~~~~~~~~~~~~
    
.. TODO use pyzmq-static dev
    
This section installs the requirements needed to run SCOOP::
    
    [downloads]$ wget http://download.zeromq.org/zeromq-2.2.0.tar.gz
    [downloads]$ tar xfvz zeromq-2.2.0.tar.gz && cd zeromq-2.2.0
    [zeromq-2.2.0]$ ./configure --prefix=$HOME/zmq/ && make && make install && cd ..
    [downloads]$ pip install pyzmq --install-option="--zmq=$HOME/zmq"
    [downloads]$ pip install -U greenlet==dev

    
.. TODO don't talk about mercurial
    
If you don't already have mercurial or SCOOP, you can use this section as reference::    

    [downloads]$ pip install mercurial
    [downloads]$ hg clone https://code.google.com/p/scoop/ ./scoop/
    [downloads]$ cd scoop/ && python setup.py install
    
.. _ssh-keys-information:

Remote usage
~~~~~~~~~~~~
    
Ensure your ssh keys are up-to-date and authorized on your remote hosts. You should log into every system that will be a foreign worker used by scoop and verify that you've got your public ssh key in the ``~/.ssh/authorized_keys2`` file on the remote systems. If you have a shared ``/home/`` over your systems, you can do as such::
    
    [~]$ mkdir ~/.ssh; cd ~/.ssh
    [.ssh]$ ssh-keygen -t dsa
    [.ssh]$ cat id_dsa.pub >> authorized_keys2
    
.. note::

    If your remote hosts needs special configuration (non-default port, some specified username, etc.), you should do it in your ssh client configuration file (by default ``~/.ssh/config``). Please refer to the ssh manual as to how to configure and personalize your hosts connections.

Startup scripts (supercomputer or grid)
---------------------------------------

You must provide a startup script on systems using a scheduler. Here is provided some example startup scripts using different grid task managers.

.. note::

    **Please note that these are only examples**. Refer to the documentation of your own scheduler to get the list of every arguments you must and/or can pass to be able the run the task on your grid.

Torque (Moab & Maui)
~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for Torque::

    #!/bin/bash
    ## Please refer to your grid documentation for available flags. This is only an example.
    #PBS -l procs=16
    #PBS -V
    #PBS -N SCOOPJob

    # Path to your executable. For example, if you extracted SCOOP to $HOME/downloads/scoop
    cd $HOME/downloads/scoop/examples

    # Add any addition to your environment variables like PATH. For example, if your local python installation is in $HOME/python
    export PATH=$HOME/python/bin:$PATH
    
    # If, instead, you are using the python offered by the system, you can stipulate it's library path via PYTHONPATH
    #export PYTHONPATH=$HOME/wanted/path/lib/python+version/site-packages/:$PYTHONPATH
    # Or use VirtualEnv via virtualenvwrapper here:
    #workon yourenvironment

    # Torque sets the list of nodes allocated to our task in a file referenced by the environment variable PBS_NODEFILE.
    hosts=$(cat $PBS_NODEFILE | sed ':a;N;$!ba;s/\n/ /g')
    
    # Launch SCOOP using the hosts
    time scooprun.py --hosts $hosts -vv -N 16 fullTree.py


Sun Grid Engine (SGE)
~~~~~~~~~~~~~~~~~~~~~

Here is an example of submit file for SGE::

    ## Please refer to your grid documentation for available flags. This is only an example.
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
    # Or use VirtualEnv via virtualenvwrapper here:
    #workon yourenvironment

    # Get a list of the (routable name) hosts assigned to our task
    hosts=$(cat $PE_HOSTFILE | awk '{printf "%s ", $1}')

    # Launch the remotes workers
    time scooprun.py --hosts $hosts -vv -N 16 test-scoop.py

.. TODO Condor & autres
        ~~~~~~
