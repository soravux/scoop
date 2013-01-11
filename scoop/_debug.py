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
import scoop
import os
import pickle


def getWorkerName(workerNum, width=5, prefix='worker'):
    """Return the name of the worker
        width: 5 (100k workers)
    """
    return "{prefix}{workerNum}".format(prefix=prefix,
                                        workerNum=workerNum.zfill(width),
                                        )


scoop.DEBUG_IDENTIFIER = (getWorkerName(scoop.WORKER_NAME.decode("utf-8")),
                          scoop.BROKER_NAME.decode("utf-8"))


def getDebugIdentifier():
    return "-".join(scoop.DEBUG_IDENTIFIER)


def writeWorkerDebug(debugStats, queueLength):
    import os
    try:
        os.makedirs("debug")
    except:
        pass
    with open("debug/{0}".format(getDebugIdentifier()), 'wb') as f:
        pickle.dump(debugStats, f)
    with open("debug/{0}-QUEUE".format(getDebugIdentifier()), 'wb') as f:
        pickle.dump(queueLength, f)

