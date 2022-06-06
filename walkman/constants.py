import logging

NAME = 'walkman'
"""Software name"""

LOGGER = logging.getLogger(f"{NAME}-logger")
LOGGER.addHandler(logging.StreamHandler())
"""Global logger"""

MODULE_PACKAGE_NAME = "walkman_modules"
