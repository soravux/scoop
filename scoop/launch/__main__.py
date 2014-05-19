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

    return nb_to_launch, sys.argv[2:]


def launchBoostraps():
    """Launch the bootstrap instances in separate subprocesses"""
    worker_amount, args = getArgs()

    try:
        sys.stdout.write(str(os.getpgrp()) + "\n")
    except:
        sys.stderr.write("Could not get process group.\n")
    sys.stdout.flush()

    sys.stderr.write("Launching {0} worker(s) using {1}.\n".format(
            worker_amount,
            os.environ['SHELL'] if 'SHELL' in os.environ else "an unknown shell",
        )
    )
    sys.stderr.flush()

    processes = []
    for _ in range(worker_amount):
        command = [sys.executable, "-m", BOOTSTRAP_MODULE] + args
        sys.stderr.write("Executing '{0}'...\n".format(command))
        sys.stderr.flush()
        processes.append(Popen(command))

        # Only have a single origin
        try:
            args.remove("--origin")
        except ValueError:
            pass

    for p in processes:
        p.wait()


if __name__ == "__main__":
    launchBoostraps()