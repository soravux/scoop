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
import subprocess

baseSSH = ['ssh', '-x', '-n', '-oStrictHostKeyChecking=no']


class baseRemote(object):
    # TODO: stdout/stderr routine
    def getGroupID(self):
        try:
            self.GID = int(self.shell.stdout.readline().strip())
        except ValueError:
            self.GID = None


def remoteSSHLaunch(hostname, command, tunnelPorts=None, stdWhere=False):
    sshCommand = baseSSH
    if tunnelPorts is not None:
        sshCommand += ['-R {0}:127.0.0.1:{0}'.format(tunnelPorts[0]),
                        '-R {0}:127.0.0.1:{0}'.format(tunnelPorts[1]),
                       ]
    return subprocess.Popen(sshCommand
                            + [hostname]
                            + [" & ".join(command)],
                            stdin=subprocess.PIPE if stdWhere else None,
                            stdout=subprocess.PIPE if stdWhere else None,
                            stderr=subprocess.PIPE if stdWhere else None,
                           )