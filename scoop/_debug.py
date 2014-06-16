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
    import cPickle as pickle
except ImportError:
    import pickle

import scoop


def getDebugIdentifier():
    """Returns the unique identifier of the current worker."""
    return scoop.worker.decode().replace(":", "_")


def getDebugDirectory():
    """Returns the debug directory."""
    return os.path.join(scoop.WORKING_DIRECTORY, "debug")


def createDirectory():
    """Create a directory in a way that multiple concurrent requests won't
    be problematic."""
    try:
        os.makedirs(getDebugDirectory())
    except:
        pass


def redirectSTDOUTtoDebugFile():
    """Redirects the stdout and stderr of the current process to a file."""
    import sys
    sys.stdout = open(
        os.path.join(
            getDebugDirectory(),
            "{0}.stdout".format(getDebugIdentifier()),
        ),
        "w",
        1, # Buffering by line
        encoding="utf8",
    )
    sys.stderr = open(
        os.path.join(
            getDebugDirectory(),
            "{0}.stderr".format(getDebugIdentifier()),
        ),
        "w",
        1, # Buffering by line
        encoding="utf8",
    )


def writeWorkerDebug(debugStats, queueLength, pathSuffix="debug"):
    """Serialize the execution data using pickle and writes it into the debug
    directory."""
    createDirectory(os.path.join(getDebugDirectory(), pathSuffix))
    origin_prefix = "origin-" if scoop.IS_ORIGIN else ""
    statsFilename = os.path.join(
        getDebugDirectory(),
        pathSuffix,
        "{1}worker-{0}-STATS".format(getDebugIdentifier(), origin_prefix)
    )
    lengthFilename = os.path.join(
        getDebugDirectory(),
        pathSuffix,
        "{1}worker-{0}-QUEUE".format(getDebugIdentifier(), origin_prefix)
    )
    with open(statsFilename, 'wb') as f:
        pickle.dump(debugStats, f)
    with open(lengthFilename, 'wb') as f:
        pickle.dump(queueLength, f)