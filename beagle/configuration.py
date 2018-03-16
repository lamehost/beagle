"""
Configuration directives for the package.
"""
import os

from jsonschema import Draft4Validator, validators
from jsonschema.exceptions import ValidationError

import yaml


def extend_with_default(validator_class):
    """
    Wrapper around jsonschema validator_class to add support for default values.

    Returns:
        Extended validator_class
    """
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        """
        Function to set default values
        """
        for _property, subschema in properties.iteritems():
            if "default" in subschema:
                instance.setdefault(_property, subschema["default"])

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return validators.extend(
        validator_class, {"properties" : set_defaults},
    )

DefaultValidatingDraft4Validator = extend_with_default(Draft4Validator)


# A sample schema, like what we'd get from json.load()
CONFIGSCHEMA = {
    "title": "Configuration",
    "type": "object",
    "properties": {
        "host": {
            "type": "string",
            "default" : "localhost",
            "description": "The hostname to bind the server to"
        },
        "port": {
            "type": "integer",
            "default" : 8080,
            "minimum": 1,
            "maximum": 65535,
            "description": "The port to bind the server to"
        },
        "username": {
            "type": "string",
            "default" : "someuser",
            "description": "The username used during login authentication"
        },
        "password": {
            "type": "string",
            "default" : "somepass",
            "description": "The password used during login authentication"
        },
        "routers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "default": "router01.pop01",
                        "description": "User friendly name of the router"
                    },
                    "address": {
                        "type": "string",
                        "default": "192.0.2.1",
                        "description": "Hostname or IP address of the router"
                    },
                    "vrfs":{
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "default": "global",
                                    "description": "Name of the VRF"
                                },
                                "loopback": {
                                    "type": "string",
                                    "default": "Lo0",
                                    "description": "Name of the VRF"
                                },
                            },
                            "additionalProperties": False,
                            "required": ["name", "loopback"]
                        },
                        "minItems": 1
                    },
                    "formats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "format": {
                                    "type": "string",
                                    "default": "text/plain",
                                    "description": "Internet media type as of RFC6838"
                                },
                                "driver": {
                                    "type": "string",
                                    "default": "beagle.drivers.ios",
                                    "description": "Driver for the router"
                                }
                            },
                            "additionalProperties": False,
                            "required": ["format", "driver"]
                        },
                        "minItems": 1,
                    },
                    "location": {
                        "type": "string",
                        "default": "Somewhere on planet earth",
                        "description": "The physical location of the router"
                    },
                    "asn": {
                        "type": "integer",
                        "default": 64496,
                        "minimum": 1,
                        "maximum": 4294967296,
                        "description": "The ASN of the router"
                    }
                },
                "required": ["name", "formats", "vrfs", "location", "asn"],
                "additionalProperties": False
            },
            "minItems": 1
        },
        "webpage": {
            "type": "string",
            "default" : "html/beagle.html",
            "description": "Path to the Jinja2 template for the web page"
        },
        "limiter": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "default" : 3,
                    "minimum": 0,
                    "description": "Amount of requests per user for the\
                     time unit defining the period"
                },
                "period": {
                    "type": "string",
                    "default" : "minute",
                    "description": "Time unit defining the period",
                    "enum": ["second", "minute", "hour", "day", "month", "year"]
                }
            },
            "required": ["amount", "period"],
            "additionalProperties": False,
            "default": {'amount': 3, 'period': 'minute'}
        },
        "findreplace": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "find": {
                        "type": "string",
                        "description": """
                                        The REGEX to be found.
                                        It supports matches, for instance:

                                            (?P<words>\w+) applied to the string "somewords"

                                        Will return the following mapping that can be used with replace:

                                            {'words': 'somewords'}

                                       """
                    },
                    "replace": {
                        "type": "string",
                        "description": """
                                        The string to be used as format for the replacement.
                                        It can borrow matches from regex, for instance:

                                            "I am replacing %(words)" applied to {'words': 'somewords'}

                                        Will return the following text:

                                            I am replacing somewords
                                       """
                    }
                },
                "required": ["find", "replace"],
                "additionalProperties": False
            },
            "minItems": 0,
            "default": []
        },
        "debug": {
            "type": "boolean",
            "description": "Turns on flask debugging",
            "default": False
        },
        "runtime": {
            "type": "object",
            "properties": {
                "min": {
                    "type": "integer",
                    "default": 30,
                    "description": "Minimun runtime value the use can set"
                },
                "max": {
                    "type": "integer",
                    "default": 120,
                    "description": "Maximum runtime value the use can set"
                }
            },
            "required": ["min", "max"],
            "additionalProperties": False
        }
    },
    "required": ["username", "password", "routers"],
    "additionalProperties": False
}


def get_defaults(schema):
    """
    Gets default values from the schema

    Args:
        schema: jsonschema

    Returns:
        dict: dict with default values
    """
    result = ""
    try:
        _type = schema['type']
    except KeyError:
        return result

    if _type == 'object':
        result = dict(
            (k, get_defaults(v)) for k, v in schema['properties'].iteritems()
        )
    elif _type == 'array':
        result = [get_defaults(schema['items'])]
    else:
        try:
            result = schema['default']
        except KeyError:
            result = result

    return result


def updatedict(original, updates):
    """
    Updates the original dictionary with items in updates.
    If key already exists it overwrites the values else it creates it

    Args:
        original: original dictionary
        updates: items to be inserted in the dictionary

    Returns:
        dict: updated dictionary
    """
    for key, value in updates.items():
        if key not in original or type(value) != type(original[key]):
            original[key] = value
        elif isinstance(value, dict):
            original[key] = updatedict(original[key], value)
        else:
            original[key] = value

    return original


def keys_to_lower(item):
    """
    Normalize dict keys to lowercase.

    Args:
        dict: dict to be normalized

    Returns:
        Normalized dict
    """
    result = False
    if isinstance(item, list):
        result = [keys_to_lower(v) for v in item]
    elif isinstance(item, dict):
        result = dict((k.lower(), keys_to_lower(v)) for k, v in item.iteritems())
    else:
        result = item

    return result


def get_config(filename, lower_keys=True):
    """
    Gets default config and overwrite it with the content of filename.
    If the file does not exist, it creates it.

    Default config is generated by applying get_defaults() to CONFIGSCHEMA.
    Content of filename by assuming the content is formatted in YAML.

    Args:
        filename: name of the YAML configuration file
        lower_keys: transform keys to lowercase

    Returns:
        dict: configuration statements
    """
    if os.path.exists(filename):
        with open(filename, 'r') as stream:
            defaults = get_defaults(CONFIGSCHEMA)
            config = yaml.load(stream)
            config = updatedict(defaults, config)
            if lower_keys:
                config = keys_to_lower(config)
    else:
        config = get_defaults(CONFIGSCHEMA)
        try:
            with open(filename, 'w') as stream:
                yaml.dump(config, stream, default_flow_style=False)
                print 'Created configuration file: %s' % filename
        except IOError:
            raise IOError('Unable to create configuration file: %s' % filename)

    try:
        DefaultValidatingDraft4Validator(CONFIGSCHEMA).validate(config)
    except ValidationError, error:
        raise SyntaxError('Error while parsing configuration file: %s' % error.message)
    return config
