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
__author__ = ("Marc Parizeau", "Olivier Gagnon", "Marc-Andre Gardner",
              "Yannick Hold-Geoffroy", "Felix-Antoine Fortin",
              "Francois-Michel de Rainville")
__version__ = "0.7"
__revision__ = "2.0"

import logging


# In case SCOOP was not initialized correctly
CONFIGURATION = {}
DEBUG = False
IS_RUNNING = False
logger = logging.getLogger()
SHUTDOWN_REQUESTED = False

TIME_BETWEEN_PARTIALDEBUG = 30
TIME_BETWEEN_STATUS_REPORTS = 25
TIME_BETWEEN_STATUS_PRUNING = 60
