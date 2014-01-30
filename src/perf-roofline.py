#!/usr/bin/python
"""
    This script takes a 'perf.data' file and populates a SQL database with
    as much data as can be gleaned from it.

    Author: Emmet Caulfield
    $Id: perf-roofline.py 41 2013-08-05 14:56:04Z emmet $

"""


import sys
import re
import os
import errno
import subprocess as sub
#import sqlite3
from pysqlite2 import dbapi2 as sqlite3
import time

from util import *

PERF_MAGIC = 'PERFILE2h'
PERF_EXE   = 'perf'
PERF_HOME  = None

# We assume that the perf script to generate the database is in
# the same directory as this script, no matter where it's run from:
PERF_SCRIPT = 'perf-create-database.py'
PERF_SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))    \
        + '/' + PERF_SCRIPT
PERF_DB_PATH = 'perf.db'

def this_script():
    return os.path.basename( sys.argv[0] )


def usage():
    """Prints a usage message and bails"""
    print("USAGE: %s [datafile|program]" % this_script())
    sys.exit(1)


def kernel_version(strip_version_info=False):
    """
    Returns the kernel version from 'uname -r', optionally
    stripping the 'version information' after the first dash.
    """
    kVerCmd=['uname', '-r']
    try:
        kVer = sub.check_output(kVerCmd, stderr=sub.STDOUT)
    except sub.CalledProcessError as cpe:
        bail("Call to %s returned %d" % (cpe.cmd, cpe.returncode))

    kVer = kVer.rstrip()
    if strip_version_info:
        kVer = kVer.split('-')[0]
    return kVer


def perf_version():
    """
    Returns the 'perf' version from "perf --version"
    """
    pVerCmd=[PERF_EXE, '--version']
    try:
        pVer = sub.check_output(pVerCmd, stderr=sub.STDOUT)
        pVer = pVer.split(' ')[2].rstrip()
    except sub.CalledProcessError as cpe:
        bail("Call to %s returned %d" % (cpe.cmd, cpe.returncode))
    except IndexError as ie:
        bail('Unexpected output from "%s"' % str(pVerCmd))
    return pVer


def isa_perf_data_file( fname ):
    """
    Tests if the given filename is a perf data file by looking at the first
    few bytes.

    """
    # Let's see if the given file is there:
    try:
        fh = open( fname )
    except IOError as ioe:
        bail( str(ioe) )

    # If we get here, we have an open filehandle:
    try:
        magic = fh.read( len(PERF_MAGIC) )
    except IOError as ioe:
        bail( str(ioe) )
    finally:
        fh.close()

    if magic==PERF_MAGIC:
        log( "File '%s' is a perf data file" % fname)
        return True

    return False


def set_perf_home():
    """
    Tries pretty hard to ensure that PERF_EXEC_PATH is set; otherwise
    'perf script' may not work correctly.

    """
    PERF_HOME=os.environ.get('PERF_EXEC_PATH')
    if PERF_HOME is not None:
        log("Environment variable PERF_EXEC_PATH='%s'" % PERF_HOME)
        if os.path.isdir(PERF_HOME):
            return PERF_HOME
        log("Path '%s' does not exist or is not a directory" % PERF_HOME)
    else:
        log("Environment variable PERF_EXEC_PATH not set")

    # Check some default places:
    def scan_places():
        kVer=[kernel_version(False), kernel_version(True)]
        places=['/usr/src/linux-{}/tools/perf',
                '/usr/src/linux-headers-{}/tools/perf',
                '/opt/src/linux-{}/tools/perf',
                '/usr/local/libexec/perf-core']
        for p in places:
            for k in kVer:
                home=p.format( k )
                log("Trying '{}' for PERF_EXEC_PATH".format(home))
                if os.path.isdir( home ):
                    return home

    PERF_HOME=scan_places()
    if PERF_HOME is None:
        log("Unable to find reasonable value for PERF_EXEC_PATH")
        bail("Could not determine PERF_EXEC_PATH")

    log("Defaulting to '{}' for PERF_EXEC_PATH".format(PERF_HOME))
    os.environ['PERF_EXEC_PATH']=PERF_HOME
    return PERF_HOME


def drop_perf_event_database(dbfile=PERF_DB_PATH):
    """Drops the SQLite database by simply deleting the associated file"""
    try:
        os.unlink(dbfile)
    except OSError as ose:
        if ose.errno == errno.ENOENT:
            pass


def create_perf_event_database( infile, dbfile=PERF_DB_PATH ):
    """Generates a SQLite database from a perf data file"""

    # We can pass in the database path as a command-line argument:
    perfCmd=[PERF_EXE, 'script', '-i', infile, '-s', PERF_SCRIPT_PATH,
        dbfile]
    log( 'Running "{}" to generate database.'.format(perfCmd) )
    start = time.clock()
    try:
        rc=sub.call( perfCmd )
    except sub.CalledProcessError as cpe:
        bail("Call to {} returned {}".format(cpe.cmd, cpe.returncode))
    log( "Processed '{}' in {} seconds".format(infile, time.clock()-start) )


def create_indexes_and_views(dbfile=PERF_DB_PATH):
    start = time.clock()
    log("Creating convenience tables and indexes")
    con = sqlite3.connect(dbfile)
    try:
        con.enable_load_extension(True)
        haveExtensions = True
    except AttributeError as ae:
        warn("Sqlite3 extensions not available; some features disabled")
        haveExtensions = False

    res = con.execute("SELECT COUNT(*) FROM event;")
    rowCount, = res.fetchone()

    sql = """
        CREATE INDEX event_dso_idx    ON event(dso);
        CREATE INDEX event_comm_idx   ON event(comm);
        CREATE INDEX event_symbol_idx ON event(symbol);
        CREATE INDEX event_name_idx   ON event(name);
    """
    con.executescript( sql );

    if haveExtensions:
        sql = """
            SELECT load_extension('%s/sqlite3/sqlite3xcu.so');
            CREATE TABLE dsos AS SELECT DISTINCT dso AS name, NULL AS label, NULL AS magic FROM event;
            UPDATE dsos SET label=basename(name), magic=filetype(name);
            CREATE TABLE hierView AS
                SELECT e.comm AS comm, e.dso AS dso, e.symbol AS symbol, e.name AS event, d.label AS label,
                       d.magic AS filetype, SUM(period) AS tally, COUNT(*) AS samples, MIN(tsc) AS tsc
                    FROM event e, dsos d
                    WHERE e.dso = d.name
            GROUP BY e.comm, e.dso, e.symbol, event, label, filetype;
            DROP TABLE dsos;
        """ % os.path.dirname(sys.argv[0])
    else:
        sql = """
            CREATE TABLE hierView AS
              SELECT comm, dso, symbol, name AS event, SUM(period) AS tally, COUNT(*) AS samples, MIN(tsc) AS tsc
                FROM event
                GROUP BY comm, dso, symbol, event;
        """

    sql += """
        CREATE INDEX hierview_comm_idx   ON hierview(comm);
        CREATE INDEX hierviw_dso_idx     ON hierview(dso);
        CREATE INDEX hierview_symbol_idx ON hierview(symbol);
        CREATE INDEX hierview_event_idx  ON hierview(event);
        CREATE TABLE unique_comms   AS SELECT DISTINCT comm   AS name FROM hierView;
        CREATE TABLE unique_symbols AS SELECT DISTINCT symbol AS name FROM hierView;
        CREATE TABLE unique_events  AS SELECT DISTINCT event  AS name, SUM(tally) AS events, 
            SUM(samples) AS samples FROM hierView GROUP BY name;
        CREATE TABLE unique_dsos    AS SELECT DISTINCT dso    AS name FROM hierView;
    """

    con.executescript( sql );
    con.close();
    dt = time.clock()-start
    try:
        rate = rowCount/dt
    except ZeroDivisionError:
        rate = '<To infinity... and beyond!>'

    log("Processed {} event records in {} seconds ({} records per second)".format(rowCount, dt, rate))


def run_executable( infile ):
    bail("Input file '%s' is executable, but %s can't do that yet" %          \
            (infile, this_script()))


def main():
    # "perf script" won't work unless the PERF_EXEC_PATH environment
    # variable is set:
    set_perf_home()


    # Compare kernel and 'perf' versions:
    kVer = kernel_version(True)
    pVer = perf_version()
    if kVer != pVer:
        warn( "Kernel and perf versions don't match (%s != %s)" % (kVer,pVer))


    # If we got this far, we at least have a working 'perf', but perhaps
    # not one that matches the kernel version.
    if len(sys.argv)==1:
        infile='perf.data'
        log("No filename given, defaulting to '%s'" % infile)
    elif len(sys.argv)==2:
        infile=sys.argv[1]
    else:
        usage()

    if isa_perf_data_file( infile ):
        dbfile = infile+'.db'
        drop_perf_event_database(dbfile)
        create_perf_event_database( infile, dbfile )
        create_indexes_and_views(dbfile)
    elif os.path.isfile(infile) and os.access(infile, os.X_OK):
        run_executable( infile )
    else:
        bail( "Input file is neither perf data nor executable." )


if __name__ == '__main__':
    main()

