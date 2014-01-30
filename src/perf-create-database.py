"""
    This perf script file reads a perf.data file and populates a SQLite
    database with as much event data as we can reasonably obtain from it.

    This script contains evil, but well-documented herein, hacks to
    circumvent SQLite's inability to store 64-bit unsigned integers.

    Author: Emmet Caulfield
    $Id: perf-create-database.py 41 2013-08-05 14:56:04Z emmet $

"""

# Based on event_analyzing_sample.py
import os
import sys
import time
import sqlite3

from util import log
from perf.util.event import PerfSample

sys.path.append(os.environ['PERF_EXEC_PATH'] +      \
    '/scripts/python/Perf-Trace-Util/lib/Perf/Trace')

from perf_trace_context import *
from EventClass import *

_DEBUG_THIS = False
_START = None
_EVENT_COUNT = 0

# --=[ EVIL HACKS ]==-
#
# SQLite does not have a 64-bit unsigned integer type. Go figure. Many, if
# not most, of the values in the various 'perf' structs are u64s. We could
# just store these values as strings, but that's highly likely to hurt
# performance, so we do evil things. In particular, instruction pointer values
# for kernel routines have bit 63 set, which SQLite will interpret as negative,
# potentially buggering up sorting and whatnot. Our evil hacks essentially
# amount to "zapping" (i.e. commuting to zero) one or more MSBs in cases where:
#
#   1. the true value can later be reconstructed without loss of information
#   2. the MSB is very highly unlikely to be set
#
# For IP values
# -------------
#
# Linux uses canonical 64-bit addressing with (currently) 48-bit
# physical addresses. In this scheme, bits 0-47 are significant,
# and bits 48-63 are copies of 47. Kernel addresses therefore
# present some difficulty.
#
# 48-bit canonical virtual addresses:
#
# ffffffff...ffff  +-------------+
#                  | Can. "high" |
#                  |  (kernel)   |
# ffff8000...0000  +-------------+
#                  | Non-canon.  |
#                  | (forbidden) |
#                  |             |
# 00007fff...ffff  +-------------+
#                  | Can. "low"  |
#                  |   (user)    |
# 00000000...0000  +-------------+
#
# With 48-bit canonical addressing, however, we can safely commute
# to 0 any number of MSBs up to bit 48 without loss of information
# and store the result in SQLite as a signed 64-bit integer. We can
# then just set any cleared MSBs back to the value of bit 47, or any
# higher uncleared bit, to get back the original value.
#
# http://en.wikipedia.org/wiki/X86-64
#
# Here, On the way in, we can just unconditionally clear bit 63 (MSB)
# and then test bit 62 on the way out:

# Masks to set/clear the most significant bit (MSB) of 64-bit unsigned ints:
MASK64_CLR_MSB = 0x7fffffffffffffff
MASK64_SET_MSB = 0x8000000000000000

# Masks to set/clear the most significant nybble (MSN) of 64-bit unsigned ints:
MASK64_CLR_MSN = 0x0fffffffffffffff
MASK64_SET_MSB = 0xf000000000000000

# Mask to test bit 59 of 64-bit value with bitwise AND:
MASK64_TST_B59 = 0x0800000000000000


def database_connection():
    """
    Open/create a connection to the database whose filename is given in
    sys.argv[1]

    """
    dbfile = sys.argv[1]
    log("Opening SQLite database connection to '{}'".format(dbfile))
    con = sqlite3.connect( dbfile )
    con.isolation_level = 'DEFERRED'
    return con


def trace_begin():
    """
    Create a table for ordinary non-PEBS event data

    The table ("events") is dropped first, if it exists, to prevent unwanted
    accumulation of data from multiple runs with the same perf.data file. No
    candidate keys have yet been identified, so the table is not strictly a
    relation.

    """
    global _START
    _START = time.clock()
    log('Creating "event" table')
    con.execute("""DROP TABLE IF EXISTS event;""")
    con.execute("""
    CREATE TABLE event (
        tsc    INT8,
        ip     INT8,
        pid    INT4,
        tid    INT4,
        name   TEXT,
        symbol TEXT,
        comm   TEXT,
        dso    TEXT,
        period INT8
    );""")


#
# Create and insert event object to a database so that user could
# do more analysis with simple database commands.
#
def process_event(param_dict):
    """
    Insert event data (one row per event) into the event data table "event"

    """
    global _EVENT_COUNT
    _EVENT_COUNT += 1
    sample = PerfSample.from_string( param_dict["sample"] )

    # We zap the MSN from u64 data to avoid problems with SQLite3's
    # incapacity to handle unsigned 64-bit integers. The alternative is
    # to store them as strings, which sucks.

    # I assume that TSC will never realistically get so big as to set
    # the MSB and just zap it.
    tsc = sample.time & MASK64_CLR_MSB

    # I zap the MSB of the instruction pointer value as documented above.
    ip    = sample.ip & MASK64_CLR_MSB
    pid   = sample.pid
    tid   = sample.tid
    count = sample.period
    name  = param_dict["ev_name"]
    comm  = param_dict["comm"]

    # Symbol and dso info are not always resolved
    if (param_dict.has_key("dso")):
        dso = param_dict["dso"]
    else:
        dso = None

    if (param_dict.has_key("symbol")):
        symbol = param_dict["symbol"]
    else:
        symbol = None

    # Insert into event table:
    try:
        con.execute("insert into event values(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tsc, ip, pid, tid, name, symbol, comm, dso, count))
    except:
        log('Caught exception: ' + sys.exc_info()[0])


def trace_unhandled(event_name, context, event_fields_dict):
    print ' '.join(['%s=%s'%(k,str(v))for k,v in sorted(event_fields_dict.items())])


def trace_end():
    global _START
    log('Closing database connection')
    con.commit()
    con.close()
    dt = time.clock()-_START
    try:
        rate = _EVENT_COUNT/dt
    except ZeroDivisionError:
        rate = '<To infinity... and beyond!>'

    log('Processed {} event records in {} seconds ({} records per second)'.format(_EVENT_COUNT, dt, rate))

con = database_connection()
