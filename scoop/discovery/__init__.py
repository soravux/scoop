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
from . import minusconf
import scoop

SERVICES_DISCOVERED = []


class SCOOPool(object):
    def __init__(self, host, ports, name):
        self._host = host
        self._ports = ports
        self._name = name

    @property
    def host(self):
        """Get address of discovered broker.
        Will convert back to IPv4 accordingly."""
        # TODO Is %interfacename working?
        host = self._host
        if host[:7] == "::ffff:":
            # IPv4 address mapped to IPv6, convert back
            host = host[7:]
        return host

    @property
    def ports(self):
        return self._ports.split(",")

    @property
    def name(self):
        return self._name


def _print_error(seeker, opposite, error_str):
    import sys
    sys.stderr.write("Error from {opposite}: {error_str}\n".format(
        opposite=opposite,
        error_str=error_str,
    ))


def _seekerCallback(seeker, svca):
    global SERVICES_DISCOVERED
    SERVICES_DISCOVERED.append(
        SCOOPool(
            svca.addr,
            svca.port,
            svca.aname,
        )
    )
    scoop.logger.info("Discovery seeker has found a broker.")


def Advertise(port, stype="SCOOP", sname="Broker", advertisername="Broker",
              location=""):
    """
    stype = always SCOOP
    port = comma separated ports
    sname = broker unique name
    location = routable location (ip or dns)
    """
    scoop.logger.info("Launching advertiser...")
    service = minusconf.Service(stype, port, sname, location)
    advertiser = minusconf.ThreadAdvertiser([service], advertisername)
    advertiser.start()
    scoop.logger.info("Advertiser launched.")

    return advertiser


def Seek(stype="SCOOP", sname="Broker", advertisername=""):
    scoop.logger.info("Launching discovery seeker...")
    se = minusconf.Seeker(stype=stype, aname=advertisername, sname=sname,
                          find_callback=_seekerCallback,
                          error_callback=_print_error,
                          )
    se.run()
    # TODO: Remove the timeout and return as soon as something is found.
    return SERVICES_DISCOVERED
