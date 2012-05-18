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

__author__ = "Marc Parizeau", "Olivier Gagnon", "Marc-Andre Gardner", \
    "Yannick Hold-Geoffroy"
__version__ = "0.5"
__revision__ = "0.5.0"

IS_ORIGIN = os.environ.get('IS_ORIGIN', "1") == "1"
WORKER_NAME = os.environ.get('WORKER_NAME', "origin").encode()
BROKER_NAME = os.environ.get('BROKER_NAME', "broker").encode()
BROKER_ADDRESS = os.environ.get('BROKER_ADDRESS', "tcp://127.0.0.1:5555").encode()
META_ADDRESS = os.environ.get('META_ADDRESS', "tcp://127.0.0.1:5556").encode()
DEBUG = False
