# Beagle

BGP Looking Glass loosely modeled on REST APIs as described by [draft-mst-lgapi](https://tools.ietf.org/html/draft-mst-lgapi-07).

This implementation slightly deviates from that suggested in the draft by adding per VRF table lookups.

# Syntax
```
$ beagle -h
usage: beagle [-h] [FILE]

positional arguments:
  FILE        configuration filename (default: beagle.conf)

optional arguments:
  -h, --help  show this help message and exit
```

# Configuration
Unless asked otherwise beagle looks for a YAML file named *beagle.conf*.

Although the actual configuration file is serialized in YAML, its content is validated with the [JSON Schema](http://json-schema.org/) validation method.

Here's the current schema:

```
title: Configuration
type: object
properties: 
    host: 
        type: string
        default : localhost
        description: The hostname to bind the server to
    port: 
        type: integer
        default : 8080
        minimum: 1
        maximum: 65535
        description: The port to bind the server to   
    username: 
        type: string
        default : someuser
        description: The username used during login authentication
    password: 
        type: string
        default : somepass
        description: The password used during login authentication
    routers: 
        type: array
        items: 
            type: object
            properties: 
                name: 
                    type: string
                    default: router01.pop01
                    description: User friendly name of the router
                address: 
                    type: string
                    default: 192.0.2.1
                    description: Hostname or IP address of the router
                vrfs:
                    type: array
                    items: 
                        type: object
                        properties: 
                            name: 
                                type: string
                                default: global
                                description: Name of the VRF
                            loopback: 
                                type: string
                                default: Lo0
                                description: Name of the VRF
                        additionalProperties: False
                        required:
                            - name
                            - loopback
                    minItems: 1
                formats: 
                    type: array
                    items: 
                        type: object
                        properties: 
                            format: 
                                type: string
                                default: text/plain
                                description: Internet media type as of RFC6838
                            driver: 
                                type: string
                                default: beagle.drivers.ios
                                description: Driver for the router
                        additionalProperties: False
                        required: 
                            - format
                            - driver
                    minItems: 1
                location: 
                    type: string
                    default: Somewhere on planet earth
                    description: The physical location of the router
                asn: 
                    type: integer
                    default: 64496
                    minimum: 1
                    maximum: 4294967296
                    description: The ASN of the router
            required: 
                - name
                - formats
                - vrfs
                - location
                - asn
            additionalProperties: False
        minItems: 1
    webpage: 
        type: string
        default : html/beagle.html
        description: Path to the Jinja2 template for the web page
    limiter: 
        type: object
        properties: 
            amount: 
                type: integer
                default : 3
                minimum: 0
                description: Amount of requests per user for the\
                 time unit defining the period
            period: 
                type: string
                default : minute
                description: Time unit defining the period
                enum:
                    - second
                    - minute
                    - hour
                    - day
                    - month
                    - year
        required:
            - amount
            - period
        additionalProperties: False
        default: 
            amount: 3
            period: 'minute'
    findreplace: 
        type: array
        items: 
            type: object
            properties: 
                find: 
                    type: string
                    description: |
                        The REGEX to be found.
                        It supports matches for instance:

                            (?P<words>\w+) applied to the string somewords

                        Will return the following mapping that can be used with replace:

                            'words': 'somewords'
                replace:
                    type: string
                    description: |
                        The string to be used as format for the replacement.
                        It can borrow matches from regex for instance:

                            I am replacing %(words) applied to 'words': 'somewords'

                        Will return the following text:

                            I am replacing somewords
            required: 
                - find
                - replace
            additionalProperties: False
        minItems: 0
        default: []
    debug: 
        type: boolean
        description: Turns on flask debugging
        default: False
    runtime: 
        type: object
        properties: 
            min: 
                type: integer
                default: 30
                description: Minimun runtime value the use can set
            max: 
                type: integer
                default: 120
                description: Maximum runtime value the use can set
        required:
            - min
            - max
        additionalProperties: False
    commands:
        type: array
        items:
            type: string
        default:            
            - ping
            - traceroute
            - show route
            - show bgp summary
            - show bgp neighbors
            - show bgp
required:
    - username
    - password
    - routers
additionalProperties: False
```

# Drivers
Interoperability with the vendors is provided by pluggable hardwares.
Those privided out of the box are listed in the table below.

| Vendor | Driver |
|---------|---------|
| Cisco IOS | beagle.drivers.ios |
| Cisco IOSXR | beagle.drivers.iosxr |

Anyway it is extremely simple to write your own driver.
The *beagle.drivers.BeagleDriver* class provides the following prototype:
```
class BeagleDriver(object):
    def __init__(self, **kwargs):
        self.hostname
        self.username
        self.password = kwargs.get('password', None)
        self.drivername = kwargs.get('drivername', None)
        self.username_prompt = kwargs.get('username_prompt', '[Uu]sername.*:')
        self.password_prompt = kwargs.get('password_prompt', '[Pp]assword.*:')
        self.findreplace = kwargs.get('findreplace', [])
        self.error_re = kwargs.get('error_re', None)

        self.device = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def sub(self, text):
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
        hostname = kwargs.get('hostname', self.hostname)
        username = kwargs.get('username', self.username)
        password = kwargs.get('password', self.password)
        drivername = kwargs.get('drivername', self.drivername)
        username_prompt = kwargs.get('username_prompt', self.username_prompt)
        password_prompt = kwargs.get('password_prompt', self.password_prompt)

        self.drivername = drivername
        self.hostname = hostname
        self.username = username
        self.password = password
        self.username_prompt = username_prompt
        self.password_prompt = password_prompt

        self.device = SSH2()
        self.device.set_driver(drivername)
        self.device.set_username_prompt(username_prompt)
        self.device.set_password_prompt(password_prompt)
        if self.error_re:
            self.device.set_error_prompt(self.error_re)

        # Connect
        try:
            self.device.connect(hostname)
        except:
            raise ConnectionError(hostname)

        # Authenticate
        try:
            self.device._paramiko_auth_password(username, password)
        except:
            raise LoginError(hostname)
        self.device.proto_authenticated = True

        # Create a shell
        self.device._paramiko_shell()
        # Sync writer and listener
        self.device.expect(next(iter([_.pattern for _ in self.device.get_prompt()])))

        # Init terminal length and width
        self.device.autoinit()

        return self.device

    def close(self):
        try:
            self.device.send('exit\n')
            self.device.send('exit\n')
        except:
            pass
        self.device.close(force=True)

    def run(self, command, **kwargs):
        if not self.device or not self.device.proto_authenticated:
            self.open(**kwargs)

        try:
            self.device.execute(command)
            result = self.device.response
        except InvalidCommandException:
            raise CommandError(self.hostname, self.device.response)

        return self.sub(result)

    def ping(self, address, vrf='global', afi=1, safi=1, loopback=False):
        raise RuntimeError('Not implemented yet')

    def traceroute(self, address, vrf='global', afi=1, safi=1, loopback=False):
        raise RuntimeError('Not implemented yet')

    def show_route(self, address, vrf='global', afi=1, safi=1):
        raise RuntimeError('Not implemented yet')

    def show_bgp(self, address, vrf='global', afi=1, safi=1):
        raise RuntimeError('Not implemented yet')

    def show_bgp_neighbors(self, address, vrf='global', afi=1, safi=1):
        raise RuntimeError('Not implemented yet')

    def show_bgp_summary(self, vrf='global', afi=1, safi=1):
        raise RuntimeError('Not implemented yet')
```
