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
from __future__ import print_function
from broker import Broker
import argparse

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Starts the broker on the current computer')
    parser.add_argument('--tPort', help='The port of the task socket',
                        default = "*")
    parser.add_argument('--mPort', help="The port of the info socket",
                        default = "*")
    parser.add_argument('--debug', help="Activate the debug", action='store_true')

    args = parser.parse_args()
    this_broker = Broker("tcp://*:" + args.tPort,
                         "tcp://*:" + args.mPort,
                         debug=True if args.debug == True else False)
    try:
        this_broker.run()
    finally:
        this_broker.shutdown()
