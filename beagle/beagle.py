from __future__ import absolute_import

import os
import socket
import ipaddress

from datetime import datetime

from flask import Flask, render_template_string, current_app
from flask_restplus import Api, Resource, fields

from werkzeug.contrib.fixers import ProxyFix

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded

from beagle.drivers import get_driver
from beagle.drivers.errors import ConnectionError, LoginError, CommandError, DriverError


try:
    text = unicode
except NameError:
    text = str.encode


def validate_address(address):
    # Check if it's an hostname
    try:
        socket.gethostbyname(address)
    # Assume it's a prefix or and address
    except socket.gaierror:
        try:
            ipaddress.ip_network(unicode(address))
        except ValueError:
            raise SyntaxError(
                "Unrecognized host or address: %s" % str(address)
            )

    return True

def get_limit():
    with beagle.app_context():
        return "%(amount)d/%(period)s" % current_app.config['limiter']

def get_limit_key():
    with beagle.app_context():
        args = parser.parse_args()
        return args['id']


beagle = Flask(__name__)
beagle.wsgi_app = ProxyFix(beagle.wsgi_app)

limiter = Limiter(
    beagle,
    key_func=get_remote_address
)

# HTML Routes
@beagle.route('/')
def index_html():
    data = {}
    with beagle.app_context():
        webpage = current_app.config['webpage']
        try:
            with open(webpage) as stream:
                content = stream.read()
        except IOError:
            base_dir = os.path.dirname(os.path.realpath(__file__))
            with open(os.path.join(base_dir, webpage)) as stream:
                content = stream.read()

    return render_template_string(content, data=data)


# Init APIs
beagle_api = Api(
    beagle,
    version='1.0',
    title='Beagle',
    description='BGP Looking Glass APIs',
    doc='/doc/'
)
ns = beagle_api.namespace('api', description='Looking glass operations')


error_model = beagle_api.model('ErrorModel', {
    'status': fields.String(default='success'),
    'performed_at': fields.DateTime(dt_format='iso8601', default=datetime.utcnow()),
    'message': fields.String
})

command_data_model = beagle_api.model('CommandDataModel', {
    'performed_at': fields.DateTime(dt_format='iso8601', default=datetime.utcnow()),
    'runtime': fields.Float,
    'router': fields.String,
    'output': fields.String,
    'format': fields.String,
    'loopback': fields.Boolean(default=False)
})

command_model = beagle_api.model('CommandModel', {
    'status': fields.String(default='success'),
    'data': fields.Nested(command_data_model)
})

router_data_model = beagle_api.model('RouterDataModel', {
    'name': fields.String(),
    'formats': fields.List(
        fields.String(attribute=lambda _: _['format'])
    ),
    'vrfs': fields.List(
        fields.String(attribute=lambda _: _['name'])
    ),
    'location': fields.String,
    'asn': fields.Integer,
    'performed_at': fields.DateTime(dt_format='iso8601', default=datetime.utcnow()),
})

router_model = beagle_api.model('RouterModel', {
    'status': fields.String(default='success'),
    'data': fields.Nested(router_data_model)
})

router_list_data_router_model = beagle_api.model('RouterListDataRouterModel', {
    'name': fields.String(),
    'formats': fields.List(
        fields.String(attribute=lambda _: _['format'])
    ),
    'vrfs': fields.List(
        fields.String(attribute=lambda _: _['name'])
    ),
    'location': fields.String,
    'asn': fields.Integer,
    'id': fields.Integer
})

router_list_data_model = beagle_api.model('RouterListDataModel', {
    'routers': fields.List(
        fields.Nested(router_list_data_router_model)
    ),
    'performed_at': fields.DateTime(dt_format='iso8601', default=datetime.utcnow()),
})

router_list_model = beagle_api.model('RouterListModel', {
    'status': fields.String(default='success'),
    'data': fields.Nested(router_list_data_model)
})

router_command_data_model = beagle_api.model('RouterCommandDataModel', {
    'href': fields.String,
    'arguments': fields.String,
    'description': fields.String,
    'command': fields.String,
})

router_commands_data_model = beagle_api.model('RouterCommandsDataModel', {
    'commands': fields.List(fields.Nested(router_command_data_model)),
    'performed_at': fields.DateTime(dt_format='iso8601', default=datetime.utcnow()),
})

router_commands_model = beagle_api.model('RouterCommandsModel', {
    'status': fields.String(default='success'),
    'data': fields.Nested(router_data_model)
})


parser = beagle_api.parser()
parser.add_argument(
    'afi',
    type=int,
    required=False,
    location='args',
    help='Restrict the command and method parameters to use the specified AFI',
    default=1,
    store_missing=True
)

parser.add_argument(
    'safi',
    type=int,
    required=False,
    location='args',
    help='Restrict the command and method parameters to use the specified SAFI',
    default=1,
    store_missing=True
)

parser.add_argument(
    'vrf',
    type=text,
    required=False,
    location='args',
    help='Restrict the command and method parameters to use the specified VRF',
    default='global',
    trim=True,
    store_missing=True
)

parser.add_argument(
    'loopback',
    type=int,
    required=False,
    location='args',
    help='Source packets from the configured loopback interface. (Treated as boolean)',
    default=False,
    store_missing=True
)

parser.add_argument(
    'id',
    type=int,
    required=True,
    location='args',
    help='Run the command on the router identified by this ID.',
    default=1
)

parser.add_argument(
    'random',
    type=text,
    required=False,
    location='args',
    help='Ignored random string to prevent the client or an intermediate proxy from caching the response',
    default=None,
    ignore=True,
)

parser.add_argument(
    'runtime',
    type=int,
    required=False,
    location='args',
    help='Stop executing the command after the runtime limit (in seconds) is exceeded. A value of 0 disables the limit',
    default=30,
    store_missing=True
)

parser.add_argument(
    'format',
    type=text,
    required=False,
    location='args',
    help='Request the server to provide the output in one of the specified formats (divided by comma)',
    default="text/plain",
    store_missing=True,
    trim=True
)


@beagle_api.errorhandler(ConnectionError)
@beagle_api.errorhandler(LoginError)
@beagle_api.marshal_with(error_model)
def router_exceptions(error):
    return {'status': 'fail', 'message': error}, getattr(error, 'code', 500)

@beagle_api.errorhandler(CommandError)
@beagle_api.marshal_with(error_model)
def router_command_exceptions(error):
    return {'status': 'error', 'message': error}, getattr(error, 'code', 502)

@beagle_api.errorhandler(RateLimitExceeded)
@beagle_api.marshal_with(error_model)
def limit_exceeded_error(error):
    return {'status': 'error', 'message': error}, getattr(error, 'code', 429)

@beagle_api.errorhandler(SyntaxError)
@beagle_api.marshal_with(error_model)
def parsing_error(error):
    return {'status': 'error', 'message': error}, getattr(error, 'code', 400)


@ns.route('/v1/ping/<address>')
class Ping(Resource):
    decorators = [limiter.limit(get_limit, key_func=get_limit_key), limiter.limit(get_limit)]
    @ns.expect(parser)
    @ns.marshal_with(command_model)
    def get(self, address):
        '''
        :raises Error when the request can't be fulfilled
        '''
        args = parser.parse_args()
        with beagle.app_context():
            config = current_app.config

        if 'ping' not in config['commands']:
            beagle_api.abort(404, "Command disabled")

        # Validate input
        validate_address(address)

        if args['runtime'] > config['runtime']['max'] or \
            args['runtime'] < config['runtime']['min']:
            raise SyntaxError("Invalid runtime value: %(runtime)d" % args)

        try:
            router = config['routers'][args['id']-1]
        except IndexError:
            raise SyntaxError("Invalid router id: %(id)d" % args)

        loopback = False
        if args['loopback']:
            try:
                loopback = next(iter(([_['loopback'] for _ in router['vrfs'] if _['name'] == args['vrf']])))
            except (IndexError, StopIteration):
                raise SyntaxError(
                    "Invalid vrf table name: %(vrf)s" % args
                )

        findreplace = []
        if 'findreplace' in config:
            findreplace = config['findreplace']

        driver_name = next(iter(_['driver'] for _ in router['formats'] if args['format'] == _['format']))
        driver = get_driver(driver_name)
        if not driver:
            raise DriverError(driver_name)
        with driver(
            'text/plain',
            hostname=router['address'],
            username=config['username'],
            password=config['password'],
            findreplace=findreplace,
            timeout=args['runtime'],
            transport=router['transport']
        ) as device:
            output = device.ping(address, args['vrf'], args['afi'], args['safi'], loopback)

        result = {
            'status': 'success',
            'data': {
                'router': router['name'],
                'format': args['format'],
                'output': output,
                'loopback': loopback
            }
        }
        return result

@ns.route('/v1/traceroute/<address>')
class Traceroute(Resource):
    decorators = [limiter.limit(get_limit, key_func=get_limit_key), limiter.limit(get_limit)]
    @ns.expect(parser)
    @ns.marshal_with(command_model)
    def get(self, address):
        '''
        :raises Error when the request can't be fulfilled
        '''
        args = parser.parse_args()
        with beagle.app_context():
            config = current_app.config

        if 'traceroute' not in config['commands']:
            beagle_api.abort(404, "Command disabled")

        # Validate input
        validate_address(address)

        if args['runtime'] > config['runtime']['max'] or \
            args['runtime'] < config['runtime']['min']:
            raise SyntaxError("Invalid runtime value: %(runtime)d" % args)

        try:
            router = config['routers'][args['id']-1]
        except IndexError:
            raise SyntaxError("Invalid router id: %(id)d" % args)

        findreplace = []
        if 'findreplace' in config:
            findreplace = config['findreplace']

        loopback = False
        if args['loopback']:
            try:
                loopback = next(iter(([_['loopback'] for _ in router['vrfs'] if _['name'] == args['vrf']])))
            except (IndexError, StopIteration):
                raise SyntaxError(
                    "Invalid vrf table name: %(vrf)s" % args
                )

        driver_name = next(iter(_['driver'] for _ in router['formats'] if args['format'] == _['format']))
        driver = get_driver(driver_name)
        if not driver:
            raise DriverError(driver_name)
        with driver(
            'text/plain',
            hostname=router['address'],
            username=config['username'],
            password=config['password'],
            findreplace=findreplace,
            timeout=args['runtime'],
            transport=router['transport']
        ) as device:
            output = device.traceroute(address, args['vrf'], args['afi'], args['safi'], loopback)

        result = {
            'status': 'success',
            'data': {
                'router': router['name'],
                'format': args['format'],
                'output': output,
                'loopback': loopback
            }
        }
        return result

@ns.route('/v1/show/route/<address>')
@ns.route('/v1/show/route/<path:address>')
class ShowRoute(Resource):
    decorators = [limiter.limit(get_limit, key_func=get_limit_key), limiter.limit(get_limit)]
    @ns.expect(parser)
    @ns.marshal_with(command_model)
    def get(self, address):
        '''
        :raises Error when the request can't be fulfilled
        '''
        args = parser.parse_args()
        with beagle.app_context():
            config = current_app.config

        if 'show route' not in config['commands']:
            beagle_api.abort(404, "Command disabled")

        # Validate input
        validate_address(address)

        if args['runtime'] > config['runtime']['max'] or \
            args['runtime'] < config['runtime']['min']:
            raise SyntaxError("Invalid runtime value: %(runtime)d" % args)

        try:
            router = config['routers'][args['id']-1]
        except IndexError:
            raise SyntaxError("Invalid router id: %(id)d" % args)

        findreplace = []
        if 'findreplace' in config:
            findreplace = config['findreplace']

        driver_name = next(iter(_['driver'] for _ in router['formats'] if args['format'] == _['format']))
        driver = get_driver(driver_name)
        if not driver:
            raise DriverError(driver_name)
        with driver(
            'text/plain',
            hostname=router['address'],
            username=config['username'],
            password=config['password'],
            findreplace=findreplace,
            timeout=args['runtime'],
            transport=router['transport']
        ) as device:
            output = device.show_route(address, args['vrf'], args['afi'], args['safi'])

        result = {
            'status': 'success',
            'data': {
                'router': router['name'],
                'format': args['format'],
                'output': output
            }
        }
        return result

@ns.route('/v1/show/bgp/summary')
class ShowBgpSummary(Resource):
    decorators = [limiter.limit(get_limit, key_func=get_limit_key), limiter.limit(get_limit)]
    @ns.expect(parser)
    @ns.marshal_with(command_model)
    def get(self):
        '''
        :raises Error when the request can't be fulfilled
        '''
        args = parser.parse_args()
        with beagle.app_context():
            config = current_app.config

        if 'show bgp summary' not in config['commands']:
            beagle_api.abort(404, "Command disabled")

        if args['runtime'] > config['runtime']['max'] or \
            args['runtime'] < config['runtime']['min']:
            raise SyntaxError("Invalid runtime value: %(runtime)d" % args)

        try:
            router = config['routers'][args['id']-1]
        except IndexError:
            raise SyntaxError("Invalid router id: %(id)d" % args)

        findreplace = []
        if 'findreplace' in config:
            findreplace = config['findreplace']

        driver_name = next(iter(_['driver'] for _ in router['formats'] if args['format'] == _['format']))
        driver = get_driver(driver_name)
        if not driver:
            raise DriverError(driver_name)
        with driver(
            'text/plain',
            hostname=router['address'],
            username=config['username'],
            password=config['password'],
            findreplace=findreplace,
            timeout=args['runtime'],
            transport=router['transport']
        ) as device:
            output = device.show_bgp_summary(args['vrf'], args['afi'], args['safi'])

        result = {
            'status': 'success',
            'data': {
                'router': router['name'],
                'format': args['format'],
                'output': output
            }
        }
        return result

@ns.route('/v1/show/bgp/neighbors/<address>')
class ShowBgpNeighbors(Resource):
    decorators = [limiter.limit(get_limit, key_func=get_limit_key), limiter.limit(get_limit)]
    @ns.expect(parser)
    @ns.marshal_with(command_model)
    def get(self, address):
        '''
        :raises Error when the request can't be fulfilled
        '''
        args = parser.parse_args()
        with beagle.app_context():
            config = current_app.config

        if 'show bgp neighbors' not in config['commands']:
            beagle_api.abort(404, "Command disabled")

        # Validate input
        validate_address(address)

        if args['runtime'] > config['runtime']['max'] or \
            args['runtime'] < config['runtime']['min']:
            raise SyntaxError("Invalid runtime value: %(runtime)d" % args)

        try:
            router = config['routers'][args['id']-1]
        except IndexError:
            raise SyntaxError("Invalid router id: %(id)d" % args)

        findreplace = []
        if 'findreplace' in config:
            findreplace = config['findreplace']

        driver_name = next(iter(_['driver'] for _ in router['formats'] if args['format'] == _['format']))
        driver = get_driver(driver_name)
        if not driver:
            raise DriverError(driver_name)
        with driver(
            'text/plain',
            hostname=router['address'],
            username=config['username'],
            password=config['password'],
            findreplace=findreplace,
            timeout=args['runtime'],
            transport=router['transport']
        ) as device:
            output = device.show_bgp_neighbors(address, args['vrf'], args['afi'], args['safi'])

        result = {
            'status': 'success',
            'data': {
                'router': router['name'],
                'format': args['format'],
                'output': output
            }
        }
        return result

@ns.route('/v1/show/bgp/<address>')
@ns.route('/v1/show/bgp/<path:address>')
class ShowBgp(Resource):
    decorators = [limiter.limit(get_limit, key_func=get_limit_key), limiter.limit(get_limit)]
    @ns.expect(parser)
    @ns.marshal_with(command_model)
    def get(self, address):
        '''
        :raises Error when the request can't be fulfilled
        '''
        args = parser.parse_args()
        with beagle.app_context():
            config = current_app.config

        if 'show bgp' not in config['commands']:
            beagle_api.abort(404, "Command disabled")

        # Validate input
        validate_address(address)

        if args['runtime'] > config['runtime']['max'] or \
            args['runtime'] < config['runtime']['min']:
            raise SyntaxError("Invalid runtime value: %(runtime)d" % args)

        try:
            router = config['routers'][args['id']-1]
        except IndexError:
            raise SyntaxError("Invalid router id: %(id)d" % args)

        findreplace = []
        if 'findreplace' in config:
            findreplace = config['findreplace']

        driver_name = next(iter(_['driver'] for _ in router['formats'] if args['format'] == _['format']))
        driver = get_driver(driver_name)
        if not driver:
            raise DriverError(driver_name)
        with driver(
            'text/plain',
            hostname=router['address'],
            username=config['username'],
            password=config['password'],
            findreplace=findreplace,
            timeout=args['runtime'],
            transport=router['transport']
        ) as device:
            output = device.show_bgp(address, args['vrf'], args['afi'], args['safi'])

        result = {
            'status': 'success',
            'data': {
                'router': router['name'],
                'format': args['format'],
                'output': output
            }
        }
        return result

@ns.route('/v1/routers')
class RouterList(Resource):
    @ns.marshal_with(router_list_model)
    def get(self):
        with beagle.app_context():
            routers = current_app.config['routers']

        for _ in range(len(routers)):
            routers[_]['id'] = _ + 1

        result = {
            'status': 'success',
            'data': {
                'routers': routers
            }
        }

        return result

@ns.route('/v1/routers/<int:id>')
class RouterById(Resource):
    @ns.marshal_with(router_model)
    def get(self, id):
        with beagle.app_context():
            routers = current_app.config['routers']

        try:
            data = routers[id-1]
            data['id'] = id
        except IndexError:
            beagle_api.abort(404, "Invalid router id: %d" % id)

        result = {
            'status': 'success',
            'data': data
        }

        return result

# TODO
@ns.route('/v1/commands')
class CommandsList(Resource):
    @ns.marshal_with(router_commands_model)
    def get(self):
        beagle_api.abort(501, "Not Implemented YET!")