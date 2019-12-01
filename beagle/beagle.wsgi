"""
WSGI application file for the package
"""

from __future__ import absolute_import

import os

from flask import current_app
from schemed_yaml_config import get_config
from beagle.beagle import beagle as application

# Get config file
config_file = os.environ.get('config', 'beagle.conf')

# Handle relative paths
if not os.path.isabs(config_file):
    basedir = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(basedir, config_file)

# Read config
schema_file = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'configuration.yml'
)
config = get_config(config_file, schema_file)

# Configure app
with application.app_context():
    for key, value in config.items():
        current_app.config[key] = value
