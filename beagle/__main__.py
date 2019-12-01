"""
CLI module for the package.

The only function is main()
"""

from __future__ import absolute_import

import os
import sys
import argparse

from flask import current_app

from beagle.beagle import beagle
from schemed_yaml_config import get_config

def main():
    """
    Main function for the module.

    Starts Flask servers
    """
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        metavar="FILE",
        default="beagle.conf",
        nargs='?',
        help="configuration filename (default: beagle.conf)"
    )
    args = parser.parse_args()

    # Read configuration
    config = {}
    schema_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'configuration.yml'
    )
    try:
        config = get_config(args.config, schema_file)
    except (IOError, SyntaxError) as error:
        sys.exit(error)

    with beagle.app_context():
        for key, value in config.items():
            current_app.config[key] = value

    beagle.run(
        debug=config['debug'],
        host=config['host'],
        port=config['port']
    )


if __name__ == "__main__":
    main()
