"""Some data structures from tools/perf/perf.h"""

import ctypes as ct

# struct ip_callchain {
#     u64 nr;
#     u64 ips[0];
# };
class IpCallchain(ct.Structure):
    _fields_ = [('nr', ct.c_ulonglong),
                ('ips', ct.POINTER(ct.c_ulonglong))]


class BranchFlags(ct.Structure):
    _fields_ = [('mispred', ct.c_ulonglong, 1),
                ('predicted', ct.c_ulonglong, 1),
                ('reserved', ct.c_ulonglong, 62)]
                

class BranchEntry(ct.Structure):
    _fields_ = [('from', ct.c_ulonglong),
                ('to', ct.c_ulonglong),
                ('flags', BranchFlags)]


class BranchStack(ct.Structure):
    _fields_ = [('nr', ct.c_ulonglong),
                ('entries', ct.POINTER(BranchEntry))]

