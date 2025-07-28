"""
Colored Logger for Blender Scripts and Extensions

A simple, plug-and-play colored logging solution for Blender that automatically
detects script/addon names and provides colorized console output with optional
addon preference integration for conditional logging.

Usage:
    Standalone:
        from .bl_logger import logger

        logger.debug('Debug message')
        logger.info('Info message')
        logger.warning('Warning message')
        logger.error('Error message')
        logger.critical('Critical message')

If your addon has a 'developer_print' boolProperty in its preferences,
logging will automatically be disabled when that property is False.
Otherwise, logging is enabled by default.

Compatible with Blender 4.2+ extensions and traditional addons.
"""

import logging
import os
import inspect

def _should_log() -> bool:
    """
    Check if it's OK to log based on developer_print in addon's preferences.
    Returns:
        bool: False if developer_print is False, True if it's enable or not 
        found (default behavior).
    """
    try:
        #pylint: disable=import-outside-toplevel
        import bpy

        # Get the calling module's package name
        frame = inspect.currentframe()
        while frame:
            frame_globals = frame.f_globals
            if '__package__' in frame_globals and frame_globals['__package__']:
                package_name = frame_globals['__package__']
                break
            frame = frame.f_back
        else:
            return True  # Default to logging if no package found

        # Try to get the developer_print preference
        prefs = bpy.context.preferences.addons[package_name].preferences
        return getattr(prefs, 'developer_print', True)  # Default to True if not found

    except (ImportError, KeyError, AttributeError):
        # Fallback to logging if bpy not available or addon/preference not found
        return True

# ANSI color codes - using bright colors for better visibility in Blender
COLORS = {
    'DEBUG': '\033[96m',       # Bright Cyan
    'INFO': '\033[92m',        # Bright Green
    'WARNING': '\033[93m',     # Bright Yellow
    'ERROR': '\033[91m',       # Bright Red
    'CRITICAL': '\033[95m'     # Bright Magenta
}
RESET = '\033[0m'


class ColoredFormatter(logging.Formatter):
    """
    Colors entire log lines based on log level.
    """

    def format(self, record):
        """
        Take the LogRecord instance containing log information and            
        returns it with ANSI color codes
        """
        formatted = super().format(record)
        if record.levelname in COLORS:
            return COLORS[record.levelname] + formatted + RESET
        return formatted


def _get_logger_name():
    """
    Returns appropriate logger name for Blender scripts and extensions.
    """
    if __package__:
        return __package__.rsplit('.', maxsplit=1)[-1]
    basepath = os.path.basename(__file__)
    if basepath == '':
        return "Unnamed Logger"
    return basepath


# Create and configure the logger automatically
logger_name = _get_logger_name()
logger = logging.getLogger(logger_name)

# Only setup if not already configured - prevents duplicate handlers
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()

    # Override emit method to check preferences
    def preference_aware_emit(record):
        """Only emit log record if developer_print preference allows it."""
        if _should_log():
            logging.StreamHandler.emit(handler, record)

    handler.emit = preference_aware_emit


    formatter = ColoredFormatter(
        "[%(name)s][%(levelname)-8s]  %(message)s (%(filename)s:%(lineno)d)"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

# Clear any root logger handlers that might interfere
if logging.getLogger().handlers:
    logging.getLogger().handlers.clear()

# Example usage (remove these lines when using as a module)
if __name__ == "__main__":
    logger.debug('debug test message')
    logger.info('info test message')
    logger.warning('warning test message')
    logger.error('error test message')
    logger.critical('critical test message')
