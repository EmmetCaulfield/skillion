"""Make some key structs in tools/perf/util/event.h available"""

import struct
# import perf.perf

# From <kernel source>/tools/perf/util/event.h:
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
class PerfSample():
    _oneshot = True
    _format = "QLL5QLL4PHQP"
    
    def __init__(self, buf):
        if PerfSample._oneshot:
            alt = "=" + PerfSample._format.replace('P', 'Q')
            print( len(buf), struct.calcsize(PerfSample._format), struct.calcsize(alt) )
            # 120, 136, 114
            PerfSample._oneshot = False

            
        fmt = '=QLL5QLL4PHQP'
        if fmt[0] == '=':
            fmt = fmt.replace('P','Q')
        sz = struct.calcsize(fmt)
        if len(buf) >= sz:
            value = struct.unpack(fmt, buf[:sz])
        else:
            raise Exception('Buffer is too small for format')
                    
        self.ip        = value[0]
        self.pid       = value[1]
        self.tid       = value[2]
        self.time      = value[3]
        self.addr      = value[4]
        self.id        = value[5]
        self.stream_id = value[6]
        self.period    = value[7]
        self.cpu       = value[8]
        self.raw_size  = value[9]
        
        return None
        
   
    @classmethod
    def from_string(cls, buf):
        return PerfSample( buf )

    

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
class PerfEventAttr(object):
    _format = "LLQQQQQLLQQ"

    def __init__(self, blob):
        data = struct.unpack(PerfEventAttr._format, blob)
        self.type          = data[0]    # L
        self.size          = data[1]    # L
        self.config        = data[2]    # Q
        self.sample_period = data[3]    # Q alias: sample_frequency
        self.sample_type   = data[4]    # Q
        self.read_format   = data[5]    # Q
        self.flags         = data[6]    # Q 21 fields
        self.wakeup_events = data[7]    # L alias: wakeup_watermark
        self.bp_type       = data[8]    # L
        self.bp_addr       = data[9]    # Q alias: config1
        self.bp_len        = data[0]    # Q alias: config2
