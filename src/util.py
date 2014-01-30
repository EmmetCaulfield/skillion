#!/usr/bin/python
# Hey, emacs, use -*- coding: utf-8 -*-
"""A smörgåsbord of itty-bitty utility functions"""

import os
import sys


# I snagged this from http://tinyurl.com/yk8to9f and added comments
def which(program):
    """Equivalent to shell 'which'; returns None if not found."""
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    # Check and see if 'program' has path components (i.e. is a
    # relative or absolute path rather than a single word:
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    # Otherwise, 'program' must be a bare word, so join it to the end
    # of each directory on the PATH in turn and see which one hits
    # first:
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    # If nothing hits, above, then 'program' is not on the path:
    return None

def warn(msg, logToo=True):
    """Print a warning to stderr, but keep going."""
    message = "WARNING: " + msg
    sys.stderr.write(message + ".\n")
    if logToo:
        log(message)


def log(msg):
    """Trivial log function that may be enhanced in the future."""
    log.counter += 1
    log.file.write("%04d: " % log.counter + msg + ".\n")
    log.file.flush()
# Initialization of "static" variables for log():
log.counter = 0
_logfile = "{}.log".format( os.path.basename(sys.argv[0]) )

try:
    log.file = open(_logfile, 'w')
except:
    warn("Unable to open logfile '{}' for output, using stdout" %
        _logfile, logToo=False)
    log.file = sys.stdout


def bail(msg, code=1):
    """Bug out with an error message."""
    message = "FATAL: " + msg
    log(message)
    sys.stderr.write(message + " (see log file).\n")
    sys.exit(code)
