#!/usr/bin/env python
"""
Implementation of the minusconf protocol. See http://code.google.com/p/minusconf/ for details.
Apache License 2.0, see the LICENSE file for details.

Most users will want a (Thread)Advertiser to advertise their server's location and a Seeker to find out the locations of servers and report them to a client program.

"""

import struct
import socket
import threading
import time

_PORT = 6376
_ADDRESS_4 = '239.45.99.98'
_ADDRESS_6 = 'ff08:0:0:6d69:6e75:7363:6f6e:6600'
_ADDRESSES = [_ADDRESS_4]
if socket.has_ipv6:
    _ADDRESSES.append(_ADDRESS_6)
_CHARSET = 'UTF-8'
VERSION='1.0'

# Compatibility functions
try:
    if bytes != str: # Python 3+
        _compat_bytes = lambda bytestr: bytes(bytestr, 'charmap')
    else: # 2.6+
        _compat_bytes = str
except NameError: # <2.6
    _compat_bytes = str

try:
    _compat_str = unicode
except NameError: # Python 3+
    _compat_str = str

_MAGIC = _compat_bytes('\xad\xc3\xe6\xe7')
_OPCODE_QUERY = _compat_bytes('\x01')
_OPCODE_ADVERTISEMENT = _compat_bytes('\x65')
_OPCODE_ERROR = _compat_bytes('\x6f')
_STRING_TERMINATOR = _compat_bytes('\x00')

_TTL = None
_MAX_PACKET_SIZE = 2048 # Biggest packet size this implementation will accept"""
_SEEKER_TIMEOUT = 2.0 # Timeout for seeks in s


class MinusconfError(Exception):
    def __init__(self, msg=''):
        super(MinusconfError, self).__init__()
        self.msg = msg

    def send(self, sock, to):
        _send_packet(sock, to, _OPCODE_ERROR, _encode_string(self.msg))


class _ImmutableStruct(object):
    """ Helper structure for immutable objects """

    def __setattr__(self, *args):
        raise TypeError("This structure is immutable")
    __delattr__ = __setattr__

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            super(_ImmutableStruct, self).__setattr__(k, v)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return self.__dict__ != other.__dict__

    def __lt__(self, other):
        return self.__dict__ < other.__dict__

    def __le__(self, other):
        return self.__dict__ <= other.__dict__

    def __gt__(self, other):
        return self.__dict__ > other.__dict__

    def __ge__(self, other):
        return self.__dict__ >= other.__dict__

    def __hash__(self):
        return hash(sum((hash(i) for i in self.__dict__.items())))


class _MinusconfImmutableStruct(_ImmutableStruct):
    def __init__(self, **kwargs):
        for v in kwargs.values():
            _check_val(v)

        super(_MinusconfImmutableStruct, self).__init__(**kwargs)


class Service(_MinusconfImmutableStruct):
    """ Helper structure for a service."""

    def __init__(self, stype, port, sname='', location=''):
        super(Service, self).__init__(stype=stype, port=_compat_str(port), sname=sname, location=location)

    def matches_query(self, stype, sname):
        return _string_match(stype, self.stype) and _string_match(sname, self.sname)

    def __str__(self):
        res = self.stype + ' service at '
        if self.sname != '': res += self.sname + ' '
        res += self.location + ':' + self.port

        return res

    def __repr__(self):
        return ('Service(' +
            repr(self.stype) + ', ' +
            repr(self.port) + ', ' +
            repr(self.sname) + ', ' +
            repr(self.location) + ')')


class ServiceAt(_MinusconfImmutableStruct):
    """ A service returned by an advertiser"""

    def __init__(self, aname, stype, sname, location, port, addr):
        super(ServiceAt, self).__init__(
            aname=aname, stype=stype, sname=sname, location=location, port=port, addr=addr
        )

    def matches_query_at(self, aname, stype, sname):
        return _string_match(stype, self.stype) and _string_match(sname, self.sname) and _string_match(aname, self.aname)

    @property
    def effective_location(self):
        return self.location if self.location != "" else self.addr

    def __str__(self):
        return (
            self.stype + ' service at ' +
            ((self.sname + ' ') if self.sname != '' else '') +
            self.location + ':' + self.port +
            ' (advertiser "' + self.aname + '" at ' + self.addr + ')'
            )

    def __repr__(self):
        return ('ServiceAt(' +
            repr(self.aname) + ', ' +
            repr(self.stype) + ', ' +
            repr(self.sname) + ', ' +
            repr(self.location) + ', ' +
            repr(self.port) + ', ' +
            repr(self.addr) + ')')


class Advertiser(object):
    """ Generic implementation of a -conf advertiser. You will probably want to use one of the subclasses.
    If ignore_unavailable is set, unsupported addresses (typically IPv6) are silently ignored
    """

    def __init__(self, services=[], aname=None, ignore_unavailable=True):
        super(Advertiser, self).__init__()

        self.services = services
        self.aname = aname if aname != None else socket.gethostname()
        self.port = _PORT
        self.addresses = _ADDRESSES
        self.ignore_unavailable = ignore_unavailable

    def _set_aname(self, aname):
        _check_val(aname)
        self._aname = aname
    aname = property(fget=lambda self:self._aname, fset=_set_aname)

    def run(self):
        self._init_advertiser()

        while True:
            rawdata,sender = self._sock.recvfrom(_MAX_PACKET_SIZE)
            self._handle_packet(rawdata, sender)

    def _init_advertiser(self):
        sock = _find_sock()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, struct.pack('@I', 1))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, struct.pack('@I', 1))
        if sock.family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, struct.pack('@I', 1))
        sock.bind(('', self.port))

        addrs = _resolve_addrs(self.addresses, None, self.ignore_unavailable, (sock.family,))

        for fam,to,orig_fam,orig_addr in addrs:
            try:
                _multicast_join_group(sock, orig_fam, orig_addr)
            except socket.error:
                if not self.ignore_unavailable:
                    raise

        self._sock = sock

    def _handle_packet(self, rawdata, sender):
        try:
            opcode, data = _parse_packet(rawdata)

            if opcode == _OPCODE_QUERY:
                self._handle_query(sender, data)
            elif opcode == _OPCODE_ERROR:
                pass # Explicitely prevent bouncing errors
            elif opcode == None:
                raise MinusconfError('Minusconf magic missing. See http://code.google.com/p/minusconf/source/browse/trunk/protocol.txt for details.')
            else:
                raise MinusconfError('Invalid or unsupported opcode ' + str(struct.unpack('!B', opcode)[0]))
        # Comment out for verbose error handling
        #except MinusconfError, mce:
            #mce.send(self._sock, sender)
        except MinusconfError:
            pass

    def services_matching(self, stype, sname):
        return filter(lambda svc: svc.matches_query(stype, sname), self.services)

    def _handle_query(self, sender, qrydata):
        qaname,p = _decode_string(qrydata, 0)
        qstype,p = _decode_string(qrydata, p)
        qsname,p = _decode_string(qrydata, p)

        if _string_match(qaname, self.aname):
            for svc in self.services_matching(qstype, qsname):
                rply = (
                    _encode_string(self.aname) +
                    _encode_string(svc.stype) +
                    _encode_string(svc.sname) +
                    _encode_string(svc.location) +
                    _encode_string(svc.port)
                    )

                _send_packet(self._sock, sender, _OPCODE_ADVERTISEMENT, rply)


class ConcurrentAdvertiser(Advertiser):
    # Subclasses must set _cav_started to an event

    def start_blocking(self):
        """ Start the advertiser in the background, but wait until it is ready """

        self._cav_started.clear()
        self.start()
        self._cav_started.wait()

    def _init_advertiser(self):
        try:
            super(ConcurrentAdvertiser, self)._init_advertiser()
        finally:
            self._cav_started.set()

    def wait_until_ready(self, timeout=None):
        self._cav_started.wait(timeout)

    def stop(self):
        raise NotImplementedError()

    def stop_blocking(self):
        raise NotImplementedError()


class ThreadAdvertiser(ConcurrentAdvertiser, threading.Thread):
    def __init__(self, services=[], aname=None, ignore_unavailable=True, daemon=True):
        ConcurrentAdvertiser.__init__(self, services, aname, ignore_unavailable)
        threading.Thread.__init__(self)

        self.setDaemon(daemon)

        self._cav_started = self._createEvent()
        self._ta_should_stop = self._createEvent()

    def run(self):
        self._ta_should_stop.clear()

        self._init_advertiser()

        while True:
            rawdata,sender = self._sock.recvfrom(_MAX_PACKET_SIZE)
            if self._ta_should_stop.is_set():
                break
            self._handle_packet(rawdata, sender)

    def stop(self):
        self._ta_should_stop.set()

    def stop_blocking(self):
        """ Stop the service and wait for it to be cleaned up. """
        self.stop() # The thread will be there, but will terminate upon the next message

    @staticmethod
    def _createEvent():
        res = threading.Event()

        if not hasattr(res, 'is_set'): # Python<2.6
            res.is_set = res.isSet

        return res

try:
    import multiprocessing

    class MultiprocessingAdvertiser(ConcurrentAdvertiser, multiprocessing.Process):
        """
        multiprocessing is only available for Python 2.6+.
        See http://code.google.com/p/python-multiprocessing/ for a backport.
        """
        def __init__(self, services=[], aname=None, ignore_unavailable=True, daemon=True):
            ConcurrentAdvertiser.__init__(self, services, aname, ignore_unavailable)
            multiprocessing.Process.__init__(self)

            self.daemon = daemon
            self._cav_started = multiprocessing.Event()

            self._mpa_manager = multiprocessing.Manager()
            self.services = self._mpa_manager.list(services)

        def stop(self):
            self.terminate()

        def stop_blocking(self):
            self.stop()
            self.join()
except ImportError:
    pass


class Seeker(threading.Thread):
    """ find_callback is called with (this_seeker,found_service_at)
    error_callback is called with (this seeker, sender, error message)
    """
    def __init__(self, stype='', aname='', sname='', timeout=_SEEKER_TIMEOUT, port=_PORT, addresses=_ADDRESSES, find_callback=None, error_callback=None, daemonized=True, ignore_senderrors=True):
        super(Seeker, self).__init__()

        self.timeout = timeout
        self.port = port
        self.addresses = addresses
        self.find_callback = find_callback
        self.error_callback = error_callback
        self.setDaemon(daemonized)
        self.ignore_senderrors = ignore_senderrors
        self.reset(stype, aname, sname)

    def reset(self, stype='', aname='', sname=''):
        self.stype = stype
        self.aname = aname
        self.sname = sname

    def _set_stype(self, stype):
        _check_val(stype)
        self._stype = stype
    stype = property(fget=lambda self:self._stype, fset=_set_stype)

    def _set_aname(self, aname):
        _check_val(aname)
        self._aname = aname
    aname = property(fget=lambda self:self._aname, fset=_set_aname)

    def _set_sname(self, sname):
        _check_val(sname)
        self._sname = sname
    sname = property(fget=lambda self:self._sname, fset=_set_sname)

    def run(self):
        self._init_seeker()

        if self._send_queries() > 0:
            self._read_replies()

    def run_forever(self):
        self.timeout = None
        self.run()

    def _init_seeker(self):
        self.results = set()

        self._sock = _find_sock()
        _multicast_configure_sender(self._sock, _TTL)

    def _send_queries(self):
        """ Sends queries to multiple addresses. Returns the number of successful queries. """

        res = 0

        addrs = _resolve_addrs(self.addresses, self.port, self.ignore_senderrors, [self._sock.family])
        for addr in addrs:
            try:
                self._send_query(addr[1])
                res += 1
            except:
                if not self.ignore_senderrors:
                    raise

        return res

    def _send_query(self, to):
        binqry = _encode_string(self.aname)
        binqry += _encode_string(self.stype)
        binqry += _encode_string(self.sname)

        _send_packet(self._sock, to, _OPCODE_QUERY, binqry)

    def _read_replies(self):
        if self.timeout == None:
            self._sock.settimeout(None)
        else:
            starttime = time.time()

        while True:
            if self.timeout != None:
                timeout = self.timeout - (time.time() - starttime)
                if timeout < 0:
                    break

                self._sock.settimeout(timeout)

            try:
                rawdata,sender = self._sock.recvfrom(_MAX_PACKET_SIZE)
            except socket.timeout:
                break

            self._handle_packet(rawdata, sender)

    def _handle_packet(self, rawdata, sender):
        try:
            opcode,data = _parse_packet(rawdata)

            if opcode == _OPCODE_ADVERTISEMENT:
                self._handle_advertisement(data, sender)
            elif opcode == _OPCODE_ERROR:
                try:
                    error_str = _decode_string(data, 0)[0]
                except:
                    error_str = '[Error when trying to read error message ' + repr(data) + ']'

                if self.error_callback != None:
                    self.error_callback(self, sender, error_str)
            else: # Invalid opcode
                pass
        except MinusconfError: # Invalid packet
            pass

    def _handle_advertisement(self, bindata, sender):
        aname,p = _decode_string(bindata, 0)
        stype,p = _decode_string(bindata, p)
        sname,p = _decode_string(bindata, p)
        location,p = _decode_string(bindata, p)
        port,p = _decode_string(bindata, p)

        if stype == '': # servicetype must be non-empty
            return

        svca = ServiceAt(aname, stype, sname, location, port, sender[0])
        if svca.matches_query_at(self.aname, self.stype, self.sname):
            self._found_result(svca)

    def _found_result(self, result):
        if not (result in self.results):
            self.results.add(result)
            if self.find_callback != None:
                self.find_callback(self, result)

def _send_packet(sock, to, opcode, data):
    sock.sendto(_MAGIC + opcode + data, 0, to)

def _parse_packet(rawdata):
    """ Returns a tupel (opcode, minusconf-data). opcode is None if this isn't a -conf packet."""

    if (len(rawdata) < len(_MAGIC) + 1) or (_MAGIC != rawdata[:len(_MAGIC)]):
        # Wrong protocol
        return (None, None)

    opcode = rawdata[len(_MAGIC):len(_MAGIC)+1]
    payload = rawdata[len(_MAGIC)+1:]

    return (opcode, payload)

def _check_val(val):
    """ Checks whether a minusconf value contains any NUL bytes. """
    try:
        if val.find('\x00') >= 0:
            raise ValueError(repr(val) + ' contains a NUL byte')
    except AttributeError: # Not a string or compatible
        pass

def _encode_string(val):
    return val.encode(_CHARSET) + _STRING_TERMINATOR

def _decode_string(buf, pos):
    """ Decodes a string in the buffer buf, starting at position pos.
    Returns a tupel of the read string and the next byte to read.
    """
    for i in range(pos, len(buf)):
        if buf[i:i+1] == _compat_bytes('\x00'):
            try:
                return (buf[pos:i].decode(_CHARSET), i+1)
            # Uncomment the following two lines for detailled information
            #except UnicodeDecodeError as ude:
            #   raise MinusconfError(str(ude))
            except UnicodeDecodeError:
                raise MinusconfError('Not a valid ' + _CHARSET + ' string: ' + repr(buf[pos:i]))

    raise MinusconfError("Premature end of string (Forgot trailing \\0?), buf=" + repr(buf))

def _string_match(query, value):
    return query == "" or query == value

def _multicast_configure_sender(sock, ttl=None):
    if ttl != None:
        ttl_bin = struct.pack('@I', ttl)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl_bin)
        if sock.family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)

def _multicast_join_group(sock, family, addr):
    group_bin = _inet_pton(family, addr)
    if family == socket.AF_INET: # IPv4
        mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    elif family == socket.AF_INET6: # IPv6
        mreq = group_bin + struct.pack('@I', 0)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
    else:
        raise ValueError('Unsupported protocol family ' + family)

def _resolve_addrs(straddrs, port, ignore_unavailable=False, protocols=[socket.AF_INET, socket.AF_INET6]):
    """ Returns a tupel of tupels of (family, to, original_addr_family, original_addr).

    If ignore_unavailable is set, addresses for unavailable protocols are ignored.
    protocols determines the protocol family indices supported by the socket in use. """

    res = []
    for sa in straddrs:
        try:
            ais = socket.getaddrinfo(sa, port)
            for ai in ais:
                if ai[0] in protocols:
                    res.append((ai[0], ai[4], ai[0], ai[4][0]))
                    break
            else:
                # Try to convert from IPv4 to IPv6
                ai = ais[0]
                if ai[0] == socket.AF_INET and socket.AF_INET6 in protocols:
                    to = socket.getaddrinfo('::ffff:' + ai[4][0], port, socket.AF_INET6)[0][4]
                    res.append((socket.AF_INET6, to, ai[0], ai[4][0]))
        except socket.gaierror:
            if not ignore_unavailable:
                raise

    return res

def _find_sock():
    """ Create a UDP socket """
    if socket.has_ipv6:
        try:
            return socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        except socket.gaierror:
            pass # Platform lied about IPv6 support
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def _main():
    """ CLI interface """
    import sys

    if len(sys.argv) < 2:
        _usage('Expected at least one parameter!')

    sc = sys.argv[1]
    options = sys.argv[2:]
    if sc == 'a' or sc == 'advertise':
        if len(options) > 5 or len(options) < 2:
            _usage()

        stype,port = options[:2]
        advertisername = options[2] if len(options) > 2 else None
        sname = options[3] if len(options) > 3 else ''
        slocation = options[4] if len(options) > 4 else ''

        service = Service(stype, port, sname, slocation)
        advertiser = Advertiser([service], advertisername)
        advertiser.run()
    elif sc == 's' or sc == 'seek':
        if len(options) > 4:
            _usage()

        aname = options[0] if len(options) > 0 else ''
        stype = options[1] if len(options) > 1 else ''
        sname = options[2] if len(options) > 2 else ''

        se = Seeker(aname, stype, sname, find_callback=_print_result, error_callback=_print_error)
        se.run()
    else:
        _usage('Unknown subcommand "' + sys.argv[0] + '"')

def _print_result(seeker, svca):
    print ("Found " + str(svca))

def _print_error(seeker, opposite, error_str):
    import sys
    sys.stderr.write("Error from " + str(opposite) + ": " + error_str + "\n")

def _usage(note=None, and_exit=True):
    import sys

    if note != None:
        print("Error: " + note + "\n")

    print("Usage: " + sys.argv[0] + " subcommand options...")
    print("\ta[dvertise] servicetype port [advertisername [servicename [location]]]")
    print("\ts[eek]      [servicetype [advertisername [servicename]]]")
    print('Use "" for default/any value.')
    print("Examples:")
    print("\t" + sys.argv[0] + " advertise http 80 fastmachine Apache")
    print("\t" + sys.argv[0] + ' seek http "" Apache')

    if and_exit:
        sys.exit(0)

def _compat_inet_pton(family, addr):
    """ socket.inet_pton for platforms that don't have it """

    if family == socket.AF_INET:
        # inet_aton accepts some strange forms, so we use our own
        res = _compat_bytes('')
        parts = addr.split('.')
        if len(parts) != 4:
            raise ValueError('Expected 4 dot-separated numbers')

        for part in parts:
            intval = int(part, 10)
            if intval < 0 or intval > 0xff:
                raise ValueError("Invalid integer value in IPv4 address: " + str(intval))

            res = res + struct.pack('!B', intval)

        return res
    elif family == socket.AF_INET6:
        wordcount = 8
        res = _compat_bytes('')

        # IPv4 embedded?
        dotpos = addr.find('.')
        if dotpos >= 0:
            v4start = addr.rfind(':', 0, dotpos)
            if v4start == -1:
                raise ValueException("Missing colons in an IPv6 address")
            wordcount = 6
            res = socket.inet_aton(addr[v4start+1:])
            addr = addr[:v4start] + '!' # We leave a marker that the address is not finished

        # Compact version?
        compact_pos = addr.find('::')
        if compact_pos >= 0:
            if compact_pos == 0:
                addr = '0' + addr
                compact_pos += 1
            if compact_pos == len(addr)-len('::'):
                addr = addr + '0'

            addr = (addr[:compact_pos] + ':' +
                ('0:' * (wordcount - (addr.count(':') - '::'.count(':')) - 2))
                + addr[compact_pos + len('::'):])

        # Remove any dots we left
        if addr.endswith('!'):
            addr = addr[:-len('!')]

        words = addr.split(':')
        if len(words) != wordcount:
            raise ValueError('Invalid number of IPv6 hextets, expected ' + str(wordcount) + ', got ' + str(len(words)))
        for w in reversed(words):
            # 0x and negative is not valid here, but accepted by int(,16)
            if 'x' in w or '-' in w:
                raise ValueError("Invalid character in IPv6 address")

            intval = int(w, 16)
            if intval > 0xffff:
                raise ValueError("IPv6 address componenent too big")
            res = struct.pack('!H', intval) + res

        return res

    else:
        raise ValueError("Unknown protocol family " + family)

# Cover for socket_pton inavailability on some systems (non-IPv6 or Windows)
try:
    import ipaddr

    if hasattr(ipaddr.IPv4, 'packed'):
        def _inet_pton(family, addr):
            if family == socket.AF_INET:
                return ipaddr.IPv4(addr).packed
            elif family == socket.AF_INET6:
                return ipaddr.IPv6(addr).packed
            else:
                raise ValueError("Unknown protocol family " + family)
except:
    pass

if not '_inet_pton' in dir():
    if hasattr(socket, 'inet_pton'):
        _inet_pton = socket.inet_pton
    else:
        _inet_pton = _compat_inet_pton

if __name__ == '__main__':
    _main()
