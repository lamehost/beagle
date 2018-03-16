from __future__ import absolute_import

import datetime, sys, re

from beagle.drivers import BeagleDriver

from Exscript.protocols.drivers.ios import _error_re


FORMATS = {
    'text/plain': 'IOS_text'
}


def IOS(_format='text/plain', **kwargs):
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


class IOS_text(BeagleDriver):
    def __init__(self, **kwargs):
        self.drivername = 'ios'
        super(IOS_text, self).__init__(**kwargs)

        self.error_re = _error_re + [
            re.compile(r'^% Un', re.I)
        ]

    def ping(self, address, vrf='global', afi=1, safi=1, loopback=False):
        try:
            afi_safi_string = {
                1: {
                    1: 'ip'
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
            command += " source %s" % loopback

        return self.run(command)

    def traceroute(self, address, vrf='global', afi=1, safi=1, loopback=False):
        try:
            afi_safi_string = {
                1: {
                    1: 'ip'
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
            command += " source %s" % loopback

        return self.run(command)

    def show_route(self, address, vrf='global', afi=1, safi=1):
        try:
            afi_safi_string = {
                1: {
                    1: 'ip'
                },
                2: {
                    1: 'ipv6'
                }
            }[afi][safi]
        except KeyError:
            raise SyntaxError('Protocol not running: AFI=%s SAFI=%s' % (str(afi), str(safi)))
        
        command = "show"
        if vrf == 'global':
            command += ' %s route %s' % (afi_safi_string, address)
        else:
            command += ' %s route vrf %s %s' % (afi_safi_string, vrf, address)

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
