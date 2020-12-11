#
#  BSD LICENSE
#
#  Copyright (c) Crane Chu <cranechu@gmail.com>
#  Copyright (c) Wayne Gao <yfwayne@hotmail.com>
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#    * Neither the name of Intel Corporation nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-


import time
import pytest
import logging

from nvme import *


class Zone(object):
    def __init__(self, qpair, ns, slba, elba=None):
        ''' single zone or super zone.

        super zone is combined with several consecutive zones. It 
works with ioworker. 

        # Parameters
            qpair: binded qpair for zns io commands
            ns: the namespace of the zone
            slba: start lba of the zone, included
            elba: end lba of the zone, excluded
        '''
            
        self._qpair = qpair
        self._ns = ns
        self._buf = Buffer()
        self.slba = slba
        self.capacity = self._mgmt_receive(slba).data(15+64, 8+64)
        
        if elba is None:
            # init all zones involved
            self.elba = slba+self.capacity
        else:
            self.elba = elba
            
        self.slba_list = []

        self.nsze = self._ns.id_data(7, 0, cns=0, csi=0)
        logging.debug("namespace size 0x%x" % self.nsze)
        self.ncap = self._ns.id_data(15, 8, cns=0, csi=0)
        logging.debug("namespace cap 0x%x" % self.ncap)
        self.zsze = self._ns.id_data(2831, 2816, cns=5, csi=2)
        logging.debug("zone size 0x%x" % self.zsze)
        if self.zsze == 0:
            self.zsze = 0x8000
        logging.debug("create zone [0x%x, 0x%x)" % (self.slba, self.elba))

        for s in range(self.slba, self.elba, self.zsze):
            # mark lba out of capacity as uncorrectable
            logging.debug("init zone slba 0x%x" % s)
            self.slba_list.append(s)
            if self.zsze > self.capacity:
                ns.write_uncorrectable(qpair, s + self.capacity, self.zsze - self.capacity).waitdone()
                
    def _mgmt_receive(self, slba):
        self._ns.zns_mgmt_receive(self._qpair, self._buf, slba).waitdone()
        assert self._buf.data(64) == 2
        assert self._buf.data(87, 80) == slba
        return self._buf

    @property
    def state(self):
        state_name = {1: 'Empty',
                      2: 'Implicitly Opened',
                      3: 'Explicitly Opened',
                      4: 'Closed',
                      0xd: 'Read Only',
                      0xe: 'Full',
                      0xf: 'Offline'}
        s = self._mgmt_receive(self.slba).data(1+64)>>4
        return state_name[s] if s in state_name else 'Reserved'

    def close(self):
        self.action(1)

    def finish(self):
        self.action(2)

    def open(self):
        self.action(3)

    def reset(self):
        self.action(4)

    def offline(self):
        self.action(5)

    def set_descriptor_extension(self):
        self.action(0x10)

    def action(self, action, slba=None):
        if slba == None:
            slba = self.slba
        logging.debug("slba 0x%x, action %d" % (slba, action))
        self._ns.zns_mgmt_send(self._qpair, self._buf, slba, action).waitdone()

    @property
    def attributes(self):
        return self._mgmt_receive(self.slba).data(2+64)

    @property
    def wpointer(self):
        return self._mgmt_receive(self.slba).data(31+64, 24+64)

    def __repr__(self):
        return "zone slba 0x%x, state %s, capacity 0x%x, write pointer 0x%x" % \
            (self.slba, self.state, self.capacity, self.wpointer)

    def write(self, qpair, buf, offset, lba_count=1, io_flags=0,
              dword13=0, dword14=0, dword15=0, cb=None):
        logging.debug("write offset 0x%x" % offset)
        return self._ns.write(qpair, buf, self.slba+offset, lba_count,
                              io_flags, dword13, dword14, dword15, cb)

    def read(self, qpair, buf, offset, lba_count=1, io_flags=0,
             dword13=0, dword14=0, dword15=0, cb=None):
        logging.debug("read offset 0x%x" % offset)
        return self._ns.read(qpair, buf, self.slba+offset, lba_count,
                             io_flags, dword13, dword14, dword15, cb)

    def append(self, qpair, buf, slba=None, lba_count=1, cb=None):
        if slba is None:
            slba = self.slba
        return self._ns.send_cmd(opcode=0x7d, qpair=qpair, buf=buf, nsid=self._ns.nsid,
                 cdw10=slba&0xffffffff, cdw11=slba>>32, cdw12=lba_count-1,
                 cdw13=0, cdw14=0, cdw15=0, cb=cb)

    def ioworker(self, io_size=8, lba_step=None, lba_align=None,
                 lba_random=False, read_percentage=0,
                 op_percentage=None, time=10, qdepth=2,
                 iops=0, io_count=0, offset_start=0, qprio=0,
                 distribution=None, ptype=0xbeef, pvalue=100,
                 io_sequence=None,
                 output_io_per_second=None,
                 output_percentile_latency=None,
                 output_cmdlog_list=None):
        """ioworker of the zone

        Default: sequential write the zone by one pass with qd = 2
        """

        # open all zones for write
        if read_percentage != 100:
            for s in self.slba_list:
                state = self._mgmt_receive(self.slba).data(1+64)>>4
                # non empty, reset, then open
                if state != 1:
                    self.action(4, s)
                self.action(3, s)
            
        return self._ns.ioworker(io_size=io_size,
                                 lba_step=lba_step,
                                 lba_align=lba_align,
                                 lba_random=lba_random,
                                 read_percentage=read_percentage,
                                 op_percentage=op_percentage,
                                 time=time,
                                 qdepth=qdepth,
                                 region_start=self.slba,
                                 region_end=self.elba,
                                 iops=iops,
                                 io_count=io_count,
                                 lba_start=offset_start+self.slba,
                                 qprio=qprio,
                                 distribution=distribution,
                                 ptype=ptype,
                                 pvalue=pvalue,
                                 io_sequence=io_sequence,
                                 output_io_per_second=output_io_per_second,
                                 output_percentile_latency=output_percentile_latency,
                                 output_cmdlog_list=output_cmdlog_list)


def test_zns_write(nvme0n1, buf, qpair):
    Zone(qpair, nvme0n1, 0).ioworker(io_size=24, io_count=768, qdepth=16).start().close()
    Zone(qpair, nvme0n1, 0x8000).ioworker(io_size=24, io_count=768, qdepth=16).start().close()
    Zone(qpair, nvme0n1, 0x20000).ioworker(io_size=24, io_count=768, qdepth=16).start().close()
    Zone(qpair, nvme0n1, 0x28000).ioworker(io_size=24, io_count=768, qdepth=16).start().close()
    Zone(qpair, nvme0n1, 0x80000).ioworker(io_size=24, io_count=768, qdepth=16).start().close()
    Zone(qpair, nvme0n1, 0, 0x10000).ioworker(io_size=24, io_count=768*2, qdepth=16).start().close()
    Zone(qpair, nvme0n1, 0x20000, 0x30000).ioworker(io_size=24, io_count=768*2, qdepth=16).start().close()

    
    with Zone(qpair, nvme0n1, 0x4000*0,  0x4000*10).ioworker(io_size=32, io_count=384*10, qdepth=16), \
         Zone(qpair, nvme0n1, 0x4000*10, 0x4000*20).ioworker(io_size=32, io_count=384*10, qdepth=16), \
         Zone(qpair, nvme0n1, 0x4000*20, 0x4000*30).ioworker(io_size=32, io_count=384*10, qdepth=16), \
         Zone(qpair, nvme0n1, 0x4000*30, 0x4000*40).ioworker(io_size=32, io_count=384*10, qdepth=16):
        pass

