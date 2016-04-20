#!/usr/bin/env python
#
#    This file is part of Scalable COncurrent Operations in Python (SCOOP).
#
#    SCOOP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    SCOOP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with SCOOP. If not, see <http://www.gnu.org/licenses/>.
#
"""This module is executed from the launcher via SSH and is used to launch the
workers using the scoop.bootstrap module. It can detect the number of cores on
the machine and simplify the SSH command.

Usage:
python -m scoop.launch [nb_to_launch] [arguments to the bootstrap module]"""

import sys
import os
from subprocess import Popen

from scoop.utils import getCPUcount

import atexit


BOOTSTRAP_MODULE = 'scoop.bootstrap.__main__'


def getArgs():
    """Gets the arguments of the program.
    Returns a tuple containting:
    (qty to launch, arguments to pass to the bootstrap module)."""
    try:
        nb_to_launch = int(sys.argv[1])
    except:
        nb_to_launch = 0

    if nb_to_launch == 0:
        nb_to_launch = getCPUcount()

    try:
        verbosity = int(sys.argv[2])
    except:
        verbosity = 3

    return nb_to_launch, verbosity, sys.argv[3:]


def cleanupBootstraps():
    """Perform a cleanup (terminate) of the children processes."""
    for p in processes:
        try:
            p.terminate()
        except OSError:
            pass


def launchBootstraps():
    """Launch the bootstrap instances in separate subprocesses"""
    global processes
    worker_amount, verbosity, args = getArgs()
    was_origin = False

    if verbosity >= 1:
        sys.stderr.write("Launching {0} worker(s) using {1}.\n".format(
                worker_amount,
                os.environ['SHELL'] if 'SHELL' in os.environ else "an unknown shell",
            )
        )
        sys.stderr.flush()

    processes = []
    for _ in range(worker_amount):
        command = [sys.executable, "-m", BOOTSTRAP_MODULE] + args
        if verbosity >= 3:
            sys.stderr.write("Executing '{0}'...\n".format(command))
            sys.stderr.flush()
        processes.append(Popen(command))

        # Only have a single origin
        try:
            args.remove("--origin")
        except ValueError:
            pass
        else:
            was_origin = True

    if was_origin:
        # Only wait on the origin, this will return and notify the launcher
        # the the job has finished and start the cleanup phase
        try:
            processes[0].wait()
        except KeyboardInterrupt:
            pass
    else:
        for p in processes:
            p.wait()


if __name__ == "__main__":
    processes = []
    try:
        launchBootstraps()
    finally:
        cleanupBootstraps()