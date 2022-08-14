#!/usr/bin/env python

from setuptools import setup

import scoop
import sys


read_md = lambda f: open(f, 'r').read()


# Backports installation
extraPackages, extraRequires = [], []
if sys.version_info < (2, 7):
    extraPackages = ['scoop.backports']
    extraRequires = ['argparse>=1.1']


setup(name='scoop',
      version="{ver}.{rev}".format(
          ver=scoop.__version__,
          rev=scoop.__revision__,
      ),
      description='Scalable COncurrent Operations in Python',
      long_description=read_md('README.md'),
      long_description_content_type="text/markdown",
      author='SCOOP Development Team',
      author_email='scoop-users@googlegroups.com',
      url='http://pyscoop.org',
      install_requires=['greenlet>=0.3.4',
                        'pyzmq>=13.1.0'] + extraRequires,
      extras_require={'nice': ['psutil>=0.6.1']},
      packages=['scoop',
                'scoop.bootstrap',
                'scoop.launch',
                'scoop.broker',
                'scoop._comm',
                'scoop.discovery'] + extraPackages,
      platforms=['any'],
      keywords=['distributed algorithms',
                'parallel programming',
                'Concurrency',
                'Cluster programming',
                'greenlet',
                'zmq'],
      license='LGPL',
      classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Library or Lesser General Public '
        'License (LGPL)',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development',
        ],
     )
