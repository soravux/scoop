Install
=======

Requirements
------------

The software requirements for SCOOP are as follows:

* `Python <http://www.python.org/>`_ >= 2.7 or >= 3.2*
* `Greenlet <http://pypi.python.org/pypi/greenlet>`_ >= 0.3.4
* `PyZMQ <http://www.zeromq.org/bindings:python>`_ and `libzmq <http://www.zeromq.org/>`_ >= 2.2.0
* ``ssh`` for remote execution

.. note::
    
    * Python versions earlier than 2.7 and 3.2 will work, but need the 
    `argparse <http://pypi.python.org/pypi/argparse>`_ module to be installed 
    separately.

Installation
------------
    
To install SCOOP and its dependencies, use pip as such::

    pip install -U scoop
    
.. note::
    
    We **strongly** recommend that you use a 
    `virtualenv <http://pypi.python.org/pypi/virtualenv>`_ alongside with a 
    `wrapper <http://www.doughellmann.com/projects/virtualenvwrapper/>`_ 
    instead of manually handling installation paths. Please refer to their 
    documentation for more informations.

Remote usage
~~~~~~~~~~~~
    
Keep in mind that connecting to remote hosts is be done without a prompt. 
This is done by using ssh keys that allows passwordless authentication over ssh 
on your remote hosts. 
You should log into every system that will be a foreign worker used by scoop and 
verify that you've got your public ssh key in the ``~/.ssh/authorized_keys2`` 
file on the remote systems. If you have a shared ``/home/`` over your systems, 
you can do as such::
    
    [~]$ mkdir ~/.ssh; cd ~/.ssh
    [.ssh]$ ssh-keygen -t dsa
    [.ssh]$ cat id_dsa.pub >> authorized_keys2
    
.. note::

    If your remote hosts needs special configuration (non-default port, some 
    specified username, etc.), you should do it in your ssh client 
    configuration file (by default ``~/.ssh/config``). Please refer to the 
    `ssh manual <http://www.openbsd.org/cgi-bin/man.cgi?query=ssh>`_ as to how 
    to configure and personalize your hosts connections.
