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

Current schema at this URL: https://github.com/lamehost/beagle/blob/master/beagle/configuration.yml

# Drivers
Interoperability with the vendors is provided by pluggable hardwares.
Those privided out of the box are listed in the table below.

| Vendor | Driver |
|---------|---------|
| Cisco IOS | beagle.drivers.ios |
| Cisco IOSXR | beagle.drivers.iosxr |

Anyway it is extremely simple to write your own driver.
Just take a look at [beagle.drivers.BeagleDriver](https://github.com/lamehost/beagle/blob/master/beagle/drivers/__init__.py) class to get an idea.
