"""
The driver packages contains driver modules for the devices.

Every modules except __init__ must contains a class for each format.
Format classes can have arbitrary names.

The abstraction method must have the same name as of the module but in uppercase.
"""

from __future__ import absolute_import

import importlib
import re
import sys

try:
    from StringIO import StringIO # Python 2
except ImportError:
    from io import StringIO # Python 3

from Exscript import Account
from Exscript.protocols import SSH2
from Exscript.protocols import Telnet
from Exscript.protocols.exception import InvalidCommandException, DriverReplacedException

from beagle.drivers.errors import CommandError, ConnectionError, LoginError


def get_driver(name):
    """
    Returns the primary class of the modules identified by the name argument.

    Primary classes are usually functions that return a Class on a per format basis.
    For a definition of "format", please take a look at RFC6838.

    Args:
        name: The name of the module

    Returns:
        bool: False on error
        obj: The primary class of the module
    """
    try:
        module = importlib.import_module(name)
        class_name = name.split('.')[-1].upper()
        obj = getattr(module, class_name)
        return obj
    except Exception:
        return False


class BeagleDriver(object):
    """
    Base Class for driver Classes.

    Attributes:
        hostname: Hostname of the device
        username: Uername to login onto the device
        password: Password to login onto the device
        drivername: Name of the Exscript protocol driver
        username_prompt: REGEX to match the login prompt as defined by Exscript
        password_prompt REGEX to match the login prompt as defined by Exscript
        findreplace: List of findreplace dictionaries. See sub() for more details
        error_re: List of REGEXes to match errors on the device
        timeout: Timeout for the command in seconds
    """
    def __init__(self, **kwargs):
        """
        Init method of the Class.

        Args:
            hostname: Hostname of the device
            username: Uername to login onto the device
            password: Password to login onto the device
            drivername: Name of the Exscript protocol driver for the device
            username_prompt: REGEX to match the login prompt as defined by Exscript
            password_prompt REGEX to match the login prompt as defined by Exscript
            findreplace: List of findreplace dictionaries. See sub() for more details
            error_re: List of REGEXes to match errors on the device
            timeout: Timeout for the command in seconds
        """
        self.hostname = kwargs.get('hostname', None)
        self.username = kwargs.get('username', None)
        self.password = kwargs.get('password', None)
        self.drivername = kwargs.get('drivername', None)
        self.username_prompt = kwargs.get('username_prompt', '[Uu]sername.*:')
        self.password_prompt = kwargs.get('password_prompt', '[Pp]assword.*:')
        self.findreplace = kwargs.get('findreplace', [])
        self.error_re = kwargs.get('error_re', None)
        self.timeout = kwargs.get('timeout', None)
        self.transport = kwargs.get('transport', None)
        self.incremental_buffer = kwargs.get('incremental_buffer', StringIO())

        self.device = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def sub(self, text, findreplace=None):
        """
        Returns the string obtained by replacing the occurrences of find in text with replace.

        Args:
            text: Text to be transformed
            findreplace: List od dicts with the following keys:
                find: is regular expression that can contain named \
                group identified by (?P<name>...)
                replace: is a string and supports printf() format. \
                Group names can be used as a reference

        Returns:
            str: Transformed text
        """
        if findreplace:
            self.findreplace = findreplace
        if not self.findreplace:
            return text

        result = list()
        for line in text.splitlines():
            for item in self.findreplace:
                try:
                    regex = re.compile(r'%s' % item['find'])
                except re.error:
                    continue
                matches = [
                    # start, end, dictionary with matches
                    [_.start(), _.end(), _.groupdict()]
                    for _ in regex.finditer(line)
                ]
                if matches:
                    end = 0
                    oldend = 0
                    _ = list()
                    for start, end, groupdict, in matches:
                        # append from oldend (at first run equals to 0) up to the matched dict
                        _.append(line[oldend:start])
                        # replaces matches from groupdict with "replace"
                        # we have to replace boolean False matches (like None) with empty strings
                        _.append(item['replace'] % {k: (v or "") for k, v in groupdict.items()})
                        # oldend is equal to end
                        oldend = end
                    _.append(line[end:])
                    line = ''.join(_)
            result.append(line)

        return '\n'.join(result)

    def open(self, **kwargs):
        """
        Connect to and login into the device.

        Args:
            hostname: Hostname of the device
            username: Uername to login onto the device
            password: Password to login onto the device
            drivername: Name of the Exscript protocol driver for the device
            username_prompt: REGEX to match the login prompt as defined by Exscript
            password_prompt REGEX to match the login prompt as defined by Exscript

        Returns:
            obj: The device object
        """
        hostname = kwargs.get('hostname', self.hostname)
        username = kwargs.get('username', self.username)
        password = kwargs.get('password', self.password)
        drivername = kwargs.get('drivername', self.drivername)
        username_prompt = kwargs.get('username_prompt', self.username_prompt)
        password_prompt = kwargs.get('password_prompt', self.password_prompt)
        transport = kwargs.get('transport', self.transport)
        incremental_buffer = kwargs.get('incremental_buffer', self.incremental_buffer)

        self.drivername = drivername
        self.hostname = hostname
        self.username = username
        self.password = password
        self.username_prompt = username_prompt
        self.password_prompt = password_prompt
        self.transport = transport
        self.incremental_buffer = incremental_buffer

        transport = str(transport).lower()
        if transport == "ssh":
            self.device = SSH2()
        elif transport == 'telnet':
            self.device = Telnet()
        else:
            raise RuntimeError('Unrecognized transport protocol: %s' % self.transport)

        self.device.set_driver(drivername)
        self.device.set_username_prompt(username_prompt)
        self.device.set_password_prompt(password_prompt)
        if self.error_re:
            self.device.set_error_prompt(self.error_re)
        else:
            self.error_re = self.device.get_error_prompt()

        if self.timeout:
            self.device.set_timeout(self.timeout)
        else:
            self.device.get_timeout()

        # Connect
        try:
            self.device.connect(hostname)
        except:
            raise ConnectionError(hostname)

        # Authenticate
        try:
            self.device.authenticate(Account(self.username, self.password))
        except:
            raise LoginError(hostname)

        # Init terminal length and width
        self.device.autoinit()

        return self.device

    def close(self):
        """
        Disconnects from the device

        Returns:
            bool: Always returns True
        """
        try:
            self.device.send('exit\n')
            self.device.send('exit\n')
        except Exception:
            pass
        self.device.close(force=True)

        return True

    def run(self, command, **kwargs):
        """
        Executes command on the device.

        Args:
            command: String of the command to be executed
            hostname: Hostname of the device
            username: Uername to login onto the device
            password: Password to login onto the device
            drivername: Name of the Exscript protocol driver for the device
            username_prompt: REGEX to match the login prompt as defined by Exscript
            password_prompt REGEX to match the login prompt as defined by Exscript

        Returns:
            str: Output of the command after sub() has been applied
        """
        if not self.device or not self.device.proto_authenticated:
            self.open(**kwargs)

        def event_handler(arg):
            self.incremental_buffer.write(arg)

        try:
            # Connect a data event listener
            self.device.data_received_event.connect(event_handler)
            self.device.execute(command)
            result = self.device.response
            # Disconnect data event listener
            self.device.data_received_event.disconnect(event_handler)
        except InvalidCommandException:
            raise CommandError(self.hostname, self.device.response)

        return self.sub(result)

    def ping(self, address, vrf='global', afi=1, safi=1, loopback=False):
        """
        Placeholder for the actual ping method.

        Args:
            address: IP address or hostname to ping
            vrf: VRF for IP route lookup
            afi: BGP AFI identifier
            safi: BGP SAFI identifier
            loopback: Name of the loopback interface

        Returns:
            Always raises error.
            Actual function will return output of the ping command modified by sub()
        """
        raise RuntimeError('Not implemented yet')

    def traceroute(self, address, vrf='global', afi=1, safi=1, loopback=False):
        """
        Placeholder for the actual traceroute method.

        Args:
            address: IP address or hostname to traceroute
            vrf: VRF for IP route lookup
            afi: BGP AFI identifier
            safi: BGP SAFI identifier
            loopback: Name of the loopback interface

        Returns:
            Always raises error.
            Actual function will return output of the traceroute command modified by sub()
        """
        raise RuntimeError('Not implemented yet')

    def show_route(self, address, vrf='global', afi=1, safi=1):
        """
        Placeholder for the actual show route method.

        Args:
            address: IP address to lookup the route
            vrf: VRF for route lookup
            afi: BGP AFI identifier
            safi: BGP SAFI identifier
            loopback: Name of the loopback interface

        Returns:
            Always raises error.
            Actual function will return output of the show route command modified by sub()
        """
        raise RuntimeError('Not implemented yet')

    def show_bgp(self, address, vrf='global', afi=1, safi=1):
        """
        Placeholder for the actual show BGP route method.

        Args:
            address: IP address to lookup the BGP route
            vrf: VRF for BGP route lookup
            afi: BGP AFI identifier
            safi: BGP SAFI identifier
            loopback: Name of the loopback interface

        Returns:
            Always raises error.
            Actual function will return output of the show BGP route command modified by sub()
        """
        raise RuntimeError('Not implemented yet')

    def show_bgp_neighbors(self, address, vrf='global', afi=1, safi=1):
        """
        Placeholder for the actual show bgp neighbor method.

        Args:
            address: Address of the neighbor
            vrf: VRF of the neighor
            afi: BGP AFI identifier
            safi: BGP SAFI identifier

        Returns:
            Always raises error.
            Actual function will return output of the show bgp neighbor command modified by sub()
        """
        raise RuntimeError('Not implemented yet')

    def show_bgp_summary(self, vrf='global', afi=1, safi=1):
        """
        Placeholder for the actual show bgp summary method.

        Args:
            vrf: VRF for the summary
            afi: BGP AFI identifier
            safi: BGP SAFI identifier

        Returns:
            Always raises error.
            Actual function will return output of the show bgp summary command modified by sub()
        """
        raise RuntimeError('Not implemented yet')
