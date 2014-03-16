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
    return scoop.worker.decode().replace(":", "_")


def writeWorkerDebug(debugStats, queueLength, path="debug"):
    import os
    try:
        os.makedirs(path)
    except:
        pass
    statsFilename = os.path.join(
        path,
        "worker-{0}-STATS".format(getDebugIdentifier())
    )
    lengthFilename = os.path.join(
        path,
        "worker-{0}-QUEUE".format(getDebugIdentifier())
    )
    with open(statsFilename, 'wb') as f:
        pickle.dump(debugStats, f)
    with open(lengthFilename, 'wb') as f:
        pickle.dump(queueLength, f)

