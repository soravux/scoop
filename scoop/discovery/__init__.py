

from . import minusconf


SERVICES_DISCOVERED = []

class SCOOPPool(object):
    def __init__(self, host, ports):
        self.host = host
        self.ports = ports

    def getHost(self):
        return self.host

    def getPorts(self):
        return self.ports.split(",")


def _seekerCallback(seeker, svca):
    global SERVICES_DISCOVERED
    SERVICES_DISCOVERED.append(
        SCOOPool(
            svca.location,
            svca.port
        ),
    )


def Advertise(port, stype="SCOOP", sname="Broker", advertisername="Broker",
              location=""):
    """
    stype = always SCOOP
    port = comma separated ports
    sname = broker unique name
    location = routable location (ip or dns)
    """
    service = minusconf.Service(stype, port, sname, location)
    advertiser = minusconf.ThreadAdvertiser([service], advertisername)
    advertiser.start()


def Seek(stype="SCOOP", sname="Broker"):
    se = minusconf.Seeker(aname, stype, sname,
                find_callback=_seekerCallback,
                error_callback=_print_error,
                )
    se.run()
    return SERVICES_DISCOVERED