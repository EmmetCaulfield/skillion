"""Make some key structs in tools/perf/util/event.h available"""

import ctypes as ct
import perf.perf

#==============================================================================
# struct perf_event_attr -> class PerfEventAttr
#------------------------------------------------------------------------------
# struct perf_event_attr {
#     __u32        type;                L
#     __u32        size;                L
#     __u64        config;              Q
#     union {                           Q
#         __u64    sample_period;
#         __u64    sample_freq;
#     };
#     __u64        sample_type;         Q
#     __u64        read_format;         Q
#
#     __u64                             Q (flags)
#                  disabled       :  1, /* off by default        */
#                  inherit        :  1, /* children inherit it   */
#                  pinned         :  1, /* must always be on PMU */
#                  exclusive      :  1, /* only group on PMU     */
#                  exclude_user   :  1, /* don't count user      */
#                  exclude_kernel :  1, /* ditto kernel          */
#                  exclude_hv     :  1, /* ditto hypervisor      */
#                  exclude_idle   :  1, /* don't count when idle */
#                  mmap           :  1, /* include mmap data     */
#                  comm           :  1, /* include comm data     */
#                  freq           :  1, /* use freq, not period  */
#                  inherit_stat   :  1, /* per task counts       */
#                  enable_on_exec :  1, /* next exec enables     */
#                  task           :  1, /* trace fork/exit       */
#                  watermark      :  1, /* wakeup_watermark      */
#                  precise_ip     :  2, /* skid constraint       */
#                  mmap_data      :  1, /* non-exec mmap data    */
#                  sample_id_all  :  1, /* sample_type all events */
#                  exclude_host   :  1, /* don't count in host   */
#                  exclude_guest  :  1, /* don't count in guest  */
#                  __reserved_1   : 43;
#
#     union {                           L
#         __u32    wakeup_events;    /* wakeup every n events */
#         __u32    wakeup_watermark; /* bytes before wakeup   */
#     };
#
#     __u32        bp_type;             L
#     union {                           Q
#         __u64    bp_addr;
#         __u64    config1; /* extension of config */
#     };
#     union {                           Q
#         __u64    bp_len;
#         __u64    config2; /* extension of config1 */
#     };
# };
#
# EVATTR_UNPACK_FORMAT = "LLQQQQQLLQQ"
#------------------------------------------------------------------------------

class _EventAttrSampleUnion(ct.Union):
    """Realizes the anonymous inline union with sample_* members"""
    _fields_ = [('sample_period',  ct.c_ulonglong),
                ('sample_freq',    ct.c_ulonglong)]

    def __init__(self):
        super(_EventAttrSampleUnion, self).__init__()



class _EventAttrFlagsBitfield(ct.Structure):
    """Realizes the anonymous inline struct with bitfields"""
    _fields_ = [('disabled',       ct.c_ulonglong,  1),  # 1
                ('inherit',        ct.c_ulonglong,  1),  # 2
                ('pinned',         ct.c_ulonglong,  1),  # 3
                ('exclusive',      ct.c_ulonglong,  1),  # 4
                ('exclude_user',   ct.c_ulonglong,  1),  # 5
                ('exclude_kernel', ct.c_ulonglong,  1),  # 6
                ('exclude_hv',     ct.c_ulonglong,  1),  # 7
                ('exclude_idle',   ct.c_ulonglong,  1),  # 8
                ('mmap',           ct.c_ulonglong,  1),  # 9
                ('comm',           ct.c_ulonglong,  1),  # 10
                ('freq',           ct.c_ulonglong,  1),  # 11
                ('inherit_stat',   ct.c_ulonglong,  1),  # 12
                ('enable_on_exec', ct.c_ulonglong,  1),  # 13
                ('task',           ct.c_ulonglong,  1),  # 14
                ('watermark',      ct.c_ulonglong,  1),  # 15
                #
                # precise_ip:
                #
                #  0 - SAMPLE_IP can have arbitrary skid
                #  1 - SAMPLE_IP must have constant skid
                #  2 - SAMPLE_IP requested to have 0 skid
                #  3 - SAMPLE_IP must have 0 skid
                #
                #  See also PERF_RECORD_MISC_EXACT_IP
                #
                ('precise_ip',     ct.c_ulonglong,  2),  # 17
                ('mmap_data',      ct.c_ulonglong,  1),  # 18
                ('sample_id_all',  ct.c_ulonglong,  1),  # 19
                ('exclude_host',   ct.c_ulonglong,  1),  # 20
                ('exclude_guest',  ct.c_ulonglong,  1),  # 21
                ('__reserved_1',   ct.c_ulonglong, 43)]  # 64

    def __init__(self):
        super(_EventAttrFlagsBitfield, self).__init__()


class _EventAttrWakeupUnion(ct.Union):
    """Realizes the anonymous inline union with wakeup_ members"""
    _fields_ = [('wakeup_events',    ct.c_ulong),
                ('wakeup_watermark', ct.c_ulong)]

    def __init__(self):
        super(_EventAttrWakeupUnion, self).__init__()


class _EventAttrBpAddrUnion(ct.Union):
    """Realizes the anonymous inline union with first member bp_addr"""
    _fields_ = [('bp_addr', ct.c_ulonglong),
                ('config1', ct.c_ulonglong)]

    def __init__(self):
        super(_EventAttrBpAddrUnion, self).__init__()


class _EventAttrBpLenUnion(ct.Union):
    """Realizes the anonymous inline union with first member bp_len"""
    _fields_ = [('bp_len',  ct.c_ulonglong),
                ('config2', ct.c_ulonglong)]

    def __init__(self):
        super(_EventAttrBpLenUnion, self).__init__()


class PerfEventAttr(ct.Structure):
    """Realizes the perf_event_attr structure"""
    _anonymous_ = ('_sample_u', '_flags', '_wakeup_u', '_bpaddr_u', '_bplen_u')
    _fields_ = [('type',        ct.c_ulong              ),
                ('size',        ct.c_ulong              ),
                ('config',      ct.c_ulonglong          ),
                ('_sample_u',   _EventAttrSampleUnion   ),
                ('sample_type', ct.c_ulonglong          ),
                ('read_format', ct.c_ulonglong          ),
                ('_flags',      _EventAttrFlagsBitfield ),
                ('_wakeup_u',   _EventAttrWakeupUnion   ),
                ('bp_type',     ct.c_ulong              ),
                ('_bpaddr_u',   _EventAttrBpAddrUnion   ),
                ('_bplen_u',    _EventAttrBpLenUnion    )]
                
    def __init__(self):
        super(PerfEventAttr, self).__init__()


    @classmethod
    def from_string(cls, arg):
        """Substitute for from_buffer() that works on strings"""
        buf = ct.create_string_buffer(bytes(arg))
        return super(cls).from_buffer(buf)

#------------------------------------------------------------------------------


#==============================================================================
# struct perf_sample -> class PerfSample
#------------------------------------------------------------------------------
#
# struct perf_sample {
#      u64 ip;                              Q
#      u32 pid, tid;                        LL
#      u64 time;                            Q
#      u64 addr;                            Q
#      u64 id;                              Q
#      u64 stream_id;                       Q
#      u64 period;                          Q
#      u32 cpu;                             L
#      u32 raw_size;                        L
#      void *raw_data;                      P
#      struct ip_callchain *callchain;      P
#      struct branch_stack *branch_stack;   P
#      struct regs_dump  user_regs;         {P}
#      struct stack_dump user_stack;        {HQP}
# };


# struct regs_dump {
#     u64 *regs;
# };
class RegsDump(ct.Structure):
    _fields_ = [('regs', ct.POINTER(ct.c_ulonglong))]


# struct stack_dump {
#     u16 offset;
#     u64 size;
#     char *data;
# };
class StackDump(ct.Structure):
    _fields_ = [('offset', ct.c_ushort),            #  2
                ('size', ct.c_ulonglong),           # 10
                ('data', ct.POINTER(ct.c_char))]    # 18


class PerfSample(ct.Structure):
    _fields_ = [('ip', ct.c_ulonglong),                                 #   8
                ('pid', ct.c_ulong),                                    #  12
                ('tid', ct.c_ulong),                                    #  16
                ('time', ct.c_ulonglong),                               #  24
                ('addr', ct.c_ulonglong),                               #  32
                ('id', ct.c_ulonglong),                                 #  40
                ('stream_id', ct.c_ulonglong),                          #  48
                ('period', ct.c_ulonglong),                             #  56
                ('cpu', ct.c_ulong),                                    #  60
                ('raw_size', ct.c_ulong),                               #  64
                ('raw_data', ct.c_void_p),                              #  72
                ('ip_callchain', ct.POINTER(perf.perf.IpCallchain)),    #  80
                ('branch_stack', ct.POINTER(perf.perf.BranchStack)),    #  88
                ('user_regs', RegsDump),                                #  96
                ('user_stack', StackDump)]                              # 114
    
    @classmethod
    def from_string(cls, arg):
        """Substitute for from_buffer() that works on strings"""
        buf = ct.create_string_buffer(bytes(arg))
        return cls.from_buffer(buf)
