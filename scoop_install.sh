#!/bin/bash
set -e
wget http://www.python.org/ftp/python/3.2.3/Python-3.2.3.tar.bz2
tar xfvj Python-3.2.3.tar.bz2 && cd Python-3.2.3
./configure --prefix=$HOME/python && make && make install
export PATH=$HOME/python/bin:$PATH
echo "PATH=\$HOME/python/bin:\$PATH" >> $HOME/.bashrc
cd ..
wget --no-check-certificate http://python-distribute.org/distribute_setup.py
python distribute_setup.py
wget --no-check-certificate  https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py
wget http://download.zeromq.org/zeromq-2.2.0.tar.gz
tar xfvz zeromq-2.2.0.tar.gz && cd zeromq-2.2.0
./configure --prefix=$HOME/zmq/ && make && make install && cd ..
pip install pyzmq --install-option="--zmq=$HOME/zmq"
pip install -U greenlet==dev
pip install mercurial
hg clone https://code.google.com/p/scoop/ ./scoop/
cd scoop/ && python setup.py install