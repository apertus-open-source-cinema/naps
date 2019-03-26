"""A simple utility for logging to stderr.

Useful when redirecting stdout to a file
"""

from sys import stderr


def log(*args):
    print(*args, file=stderr)
