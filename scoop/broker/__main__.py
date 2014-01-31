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
import os
try:
    import psutil
except:
    psutil = None

from scoop.broker.broker import Broker
from signal import signal, SIGTERM, SIGINT
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Starts the broker on the"
                                                 "current computer")
    parser.add_argument('--tPort',
                        help='The port of the task socket',
                        default="*")
    parser.add_argument('--mPort',
                        help="The port of the info socket",
                        default="*")
    parser.add_argument('--nice',
                        help="Adjust the process niceness",
                        type=int,
                        default=0)
    parser.add_argument('--debug',
                        help="Activate the debug",
                        action='store_true')
    parser.add_argument('--headless',
                        help="Enforce headless (cloud-style) operation",
                        action='store_true')
    parser.add_argument('--echoGroup',
                        help="Echo the process Group ID before launch",
                        action='store_true')
    parser.add_argument('--echoPorts',
                        help="Echo the listening ports",
                        action='store_true')
    args = parser.parse_args()

    if args.echoGroup:
        import os
        import sys
        sys.stdout.write(str(os.getpgrp()) + "\n")
        sys.stdout.flush()

    thisBroker = Broker("tcp://*:" + args.tPort,
                        "tcp://*:" + args.mPort,
                        debug=args.debug,
                        headless=args.headless,
                        )

    signal(SIGTERM,
           lambda signum, stack_frame: thisBroker.shutdown())
    signal(SIGINT,
           lambda signum, stack_frame: thisBroker.shutdown())

    # Handle nicing functionnality
    if args.nice:
        if not psutil:
            scoop.logger.error("psutil not installed.")
            raise ImportError("psutil is needed for nice functionality.")
        p = psutil.Process(os.getpid())
        p.set_nice(args.nice)

    if args.echoPorts:
        import os
        import sys
        sys.stdout.write("{0},{1}\n".format(
            thisBroker.tSockPort,
            thisBroker.infoSockPort,
        ))
        sys.stdout.flush()

        thisBroker.logger.info("Using name {workerName}".format(
            workerName=thisBroker.getName(),
        ))

    try:
        thisBroker.run()
    finally:
        thisBroker.shutdown()
