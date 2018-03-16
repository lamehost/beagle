from __future__ import absolute_import

from datetime import datetime

class CommandError(Exception):
    def __init__(self, router, output):
        self.router = router
        self.output = output
        self.timestamp = datetime.utcnow()
        self.code = 502

    def __str__(self):
        return self.output

    def __repr__(self):
        return "%s: %s" % (self.__name__, self.output)

class ConnectionError(Exception):
    def __init__(self, router):
        self.router = router
        self.timestamp = datetime.utcnow()
        self.code = 500

    def __str__(self):
        return repr("Cannot connect to the device")

    def __repr__(self):
        return "%s: %s" % (self.__name__, "Unable to connect to remote host: %s" % self.router)

class LoginError(Exception):
    def __init__(self, router):
        self.router = router
        self.timestamp = datetime.utcnow()
        self.code = 500

    def __str__(self):
        return repr("Cannot login to the device")

    def __repr__(self):
        return "%s: %s" % (self.__name__, "Unable to login on remote host: %s" % self.router)
