from __future__ import absolute_import

import datetime, sys, re

from beagle.drivers import BeagleDriver


FORMATS = {
    'text/plain': 'IOSXR_text'
}


def IOSXR(_format='text/plain', **kwargs):
    """
    Abstraction method for the driver modules.
    Returns the driver Class for the specified format

    Args:
        format: String identifying the format
        **kwargs: Keyword arguments to be passed to the driver

    Returns:
        obj: The class for the format
    """
    obj = getattr(sys.modules[__name__], FORMATS[_format])
    return obj(**kwargs)


class IOSXR_text(BeagleDriver):
    def __init__(self, **kwargs):
        self.drivername = 'ios_xr'
        super(IOSXR_text, self).__init__(**kwargs)

        self.error_re = [
            re.compile(r'%Error'),
            re.compile(r'invalid input', re.I),
            re.compile(r'(?:incomplete|ambiguous) command', re.I),
            re.compile(r'connection timed out', re.I),
            re.compile(r'[^\r\n]+ not found', re.I),
            re.compile(r'bad hostname or protocol', re.I),
            re.compile(r'unknown getaddrinfo()', re.I)
        ]

    def ping(self, address, vrf='global', afi=1, safi=1, loopback=False):
        try:
            afi_safi_string = {
                1: {
                    1: 'ipv4'
                },
                2: {
                    1: 'ipv6'
                }
            }[afi][safi]
        except KeyError:
            raise SyntaxError('Protocol not running: AFI=%s SAFI=%s' % (str(afi), str(safi)))

        command = "ping"
        if vrf == 'global':
            command += ' %s %s' % (afi_safi_string, address)
        else:
            command += ' vrf %s %s %s' % (vrf, afi_safi_string, address)

        if loopback:
            if afi == 1:
                output = self.run('show ipv4 interface %s' % loopback)
                address = next(iter([
                    next(iter(_.split(' ')[-1].split('/')))
                    for _ in output.splitlines()
                    if _.lstrip().startswith('Internet address is ')
                ]))
            else:
                output = self.run('show ipv6 interface %s' % loopback)
                address = next(iter([
                    next(iter(_.split(','))).lstrip()
                    for _ in output.splitlines()
                    if "subnet is" in _
                ]))
            command += " source %s" % address

        return self.run(command)

    def traceroute(self, address, vrf='global', afi=1, safi=1, loopback=False):
        try:
            afi_safi_string = {
                1: {
                    1: 'ipv4'
                },
                2: {
                    1: 'ipv6'
                }
            }[afi][safi]
        except KeyError:
            raise SyntaxError('Protocol not running: AFI=%s SAFI=%s' % (str(afi), str(safi)))

        command = "traceroute"
        if vrf == 'global':
            command += ' %s %s' % (afi_safi_string, address)
        else:
            command += ' vrf %s %s %s' % (vrf, afi_safi_string, address)

        if loopback:
            if afi == 1:
                output = self.run('show ipv4 interface %s' % loopback)
                address = next(iter([
                    next(iter(_.split(' ')[-1].split('/')))
                    for _ in output.splitlines()
                    if _.lstrip().startswith('Internet address is ')
                ]))
            else:
                output = self.run('show ipv6 interface %s' % loopback)
                address = next(iter([
                    next(iter(_.split(','))).lstrip()
                    for _ in output.splitlines()
                    if "subnet is" in _
                ]))
            command += " source %s" % address

        return self.run(command)

    def show_route(self, address, vrf='global', afi=1, safi=1):
        try:
            afi_safi_string = {
                1: {
                    1: 'ipv4'
                },
                2: {
                    1: 'ipv6'
                }
            }[afi][safi]
        except KeyError:
            raise SyntaxError('Protocol not running: AFI=%s SAFI=%s' % (str(afi), str(safi)))
        
        command = "show"
        if vrf == 'global':
            command += ' route %s %s' % (afi_safi_string, address)
        else:
            command += ' route vrf %s %s %s' % (vrf, afi_safi_string, address)

        return self.run(command)

    def show_bgp(self, address, vrf='global', afi=1, safi=1):
        try:
            afi_safi_string = {
                True: {
                    1: {
                        1: 'ipv4 unicast'
                    },
                    2: {
                        1: 'ipv6 unicast'
                    }
                },
                False: {
                    1: {
                        1: 'vpnv4 unicast'
                    },
                    2: {
                        1: 'vpnv6 unicast'
                    }
                }
            }[vrf == 'global'][afi][safi]
        except KeyError:
            raise SyntaxError('Protocol not running: AFI=%s SAFI=%s' % (str(afi), str(safi)))
        
        command = "show bgp"
        if vrf == 'global':
            command += ' %s %s' % (afi_safi_string, address)
        else:
            command += ' %s vrf %s %s' % (afi_safi_string, vrf, address)

        return self.run(command)

    def show_bgp_neighbors(self, address, vrf='global', afi=1, safi=1):
        try:
            afi_safi_string = {
                True: {
                    1: {
                        1: 'ipv4 unicast'
                    },
                    2: {
                        1: 'ipv6 unicast'
                    }
                },
                False: {
                    1: {
                        1: 'vpnv4 unicast'
                    },
                    2: {
                        1: 'vpnv6 unicast'
                    }
                }
            }[vrf == 'global'][afi][safi]
        except KeyError:
            raise SyntaxError('Protocol not running: AFI=%s SAFI=%s' % (str(afi), str(safi)))

        command = "show bgp"
        if vrf == 'global':
            command += ' %s %s' % (afi_safi_string, address)
        else:
            command += ' %s vrf %s neighbors %s' % (afi_safi_string, vrf, address)

        return self.run(command)


    def show_bgp_summary(self, vrf='global', afi=1, safi=1):
        return self.show_bgp('summary', vrf, afi, safi)
