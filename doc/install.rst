Install
=======

Dependencies
------------

The software requirements for SCOOP are as follows:

* `Python <http://www.python.org/>`_ >= 2.6 or >= 3.2
* `Distribute <http://packages.python.org/distribute/>`_ >= 0.6.2 or `setuptools <https://pypi.python.org/pypi/setuptools>`_ >= 0.7
* `Greenlet <http://pypi.python.org/pypi/greenlet>`_ >= 0.3.4
* `pyzmq <http://www.zeromq.org/bindings:python>`_  >= 13.1.0 and 
  `libzmq <http://www.zeromq.org/>`_ >= 3.2.0
* :program:`ssh` for remote execution

Prerequisites
-------------

Linux
~~~~~

You must have the Python headers (to compile pyzmq and greenlet) and pip
installed. These should be simple to install using the package manager
provided with your distribution.

To get the prerequisites on an Ubuntu system, execute the following in a
console::

    sudo apt-get install python-dev python-pip

Ensure that your compiler is GCC as it is the tested compiler for pyzmq and
greenlet.

Mac
~~~

The easiest way to get started is by using `Homebrew <http://brew.sh/>`_. Once
you've brewed your Python version and ZeroMQ, you are ready to install SCOOP.

Windows
~~~~~~~

Please download and install pyzmq before installing SCOOP. This can be done by
using the binary installer provided at their `download page
<https://github.com/zeromq/pyzmq/downloads>`_. These installers will provide
libzmq alongside pyzmq.

You can install pip on windows using either `Christoph Gohlke
<http://www.lfd.uci.edu/~gohlke/pythonlibs/#pip>`_ windows installers or the
get-pip.py script as shown in the `pip-installer.org webpage <http://www.pip-
installer.org/en/latest/installing.html>`_.

Installation
------------

To install SCOOP, use  `pip <http://www.pip-
installer.org/en/latest/index.html>`_ as such::

    pip install scoop

POSIX Operating systems
~~~~~~~~~~~~~~~~~~~~~~~

Connection to remote hosts is done using SSH. An implementation of SSH must
be installed in order to be able to use this feature.


Windows Operating System
~~~~~~~~~~~~~~~~~~~~~~~~
    
On Windows, this will try to compile libzmq. You can skip this compilation by
installing pyzmq using the installer available at their
`download page <https://github.com/zeromq/pyzmq/downloads>`_.
This installer installs libzmq alongside pyzmq.

Furthermore, to be able to use the multi-system capabilities of SCOOP, a SSH
implementation must be available. This may be done either by using
`Cygwin <http://www.cygwin.com/>`_ or
`OpenSSH for Windows <http://sshwindows.sourceforge.net/download/>`_.

Remote usage
------------
    
Because remote host connection needs to be done without a prompt, you must use
ssh keys to allow **passwordless authentication between every computing
node**. You should make sure that your public ssh key is contained in the
``~/.ssh/authorized_keys``  file on the remote systems (Refer to the `ssh
manual <http://www.openbsd.org/cgi-bin/man.cgi?query=ssh>`_). If you have a
shared :file:`/home/` over your systems, you can do as such::
    
    [~]$ mkdir ~/.ssh; cd ~/.ssh
    [.ssh]$ ssh-keygen -t dsa
    [.ssh]$ cat id_dsa.pub >> authorized_keys
    [.ssh]$ chmod 700 ~/.ssh ; chmod 600 ./id_dsa ; chmod 644 ./id_dsa.pub ./authorized_keys
    
.. note::

    If your remote hosts needs special configuration (non-default port, some 
    specified username, etc.), you should do it in your ssh client 
    configuration file (by default ``~/.ssh/config``).

.. note::

    The following parameters of ``ssh`` are used by SCOOP:

        * -x : Deactivates X forwarding
        * -n : Prevents reading from stdin (batch mode)
        * -oStrictHostKeyChecking=no : Allow the connection to hosts ``ssh`` sees for the first time. Without it, ``ssh`` interactively asks to accept the identity of the peer.

HPC usage
---------

If you use an Infiniband network, you may want to use an RDMA accelerated
socket alternative instead of TCP over IB. In order to do so, you can use
libsdp. This can be done by performing the following steps::

    $ wget https://www.openfabrics.org/downloads/libsdp/libsdp-1.1.108-0.17.ga6958ef.tar.gz 
    $ tar xfvz libsdp-1.1.108-0.17.ga6958ef.tar.gz
    $ cd libsdp-1.1.108
    $ ./configure --prefix=$HOME && make && make install

Once the compilation is done, you can use it by creating a file containing this
(for bash)::

    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/lib/
    export LD_PRELOAD=libsdp.so

By passing this file to the ``--prolog`` parameter of SCOOP, SDP sockets will
be used instead of TCP over IB.
