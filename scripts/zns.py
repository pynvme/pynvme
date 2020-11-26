#
#  BSD LICENSE
#
#  Copyright (c) Crane Chu <cranechu@gmail.com>
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
    def __init__(self, qpair, ns, slba):
        logging.debug("create zone at 0x%x" % slba)
        self._qpair = qpair
        self._ns = ns
        self._buf = Buffer()
        self.slba = slba
        self.capacity = self._mgmt_receive().data(15+64, 8+64)

    def _mgmt_receive(self):
        self._ns.zns_mgmt_receive(self._qpair, self._buf, self.slba).waitdone()
        assert self._buf.data(64) == 2
        assert self._buf.data(87, 80) == self.slba
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
        s = self._mgmt_receive().data(1+64)>>4
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

    def action(self, action):
        self._ns.zns_mgmt_send(self._qpair, self._buf, self.slba, action).waitdone()

    @property
    def attributes(self):
        return self._mgmt_receive().data(2+64)

    @property
    def wpointer(self):
        return self._mgmt_receive().data(31+64, 24+64)

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


    def append(self, qpair, buf, slba=None, lba_count=0, cb=None):
        if slba is None:
            slba = self.slba
        return self._ns.send_cmd(opcode=0x7d, qpair=qpair, buf=buf, nsid=self._ns.nsid,
                 cdw10=slba&0xffffffff, cdw11=slba>>32, cdw12=lba_count,
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
        return self._ns.ioworker(io_size=io_size,
                                 lba_step=lba_step,
                                 lba_align=lba_align,
                                 lba_random=lba_random,
                                 read_percentage=read_percentage,
                                 op_percentage=op_percentage,
                                 time=time,
                                 qdepth=qdepth,
                                 region_start=self.slba,
                                 region_end=self.slba+self.capacity,
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


def test_zns_framework(nvme0, nvme0n1):
    nvme0n1.format(512)
    assert type(nvme0n1) == Namespace
    assert nvme0.getfeatures(7).waitdone() == 0xf000f
    logging.info(nvme0n1.ioworker(io_size=8, io_count=1).start().close())


def test_zns_write(nvme0n1, buf, qpair):
    nvme0n1.format(512)
    zone = Zone(qpair, nvme0n1, 0)
    nvme0n1.write(qpair, buf, 0, 8).waitdone()
    zone.write(qpair, buf, 0, 8).waitdone()
    zone.write(qpair, buf, 8, 8).waitdone()
    nvme0n1.read(qpair, buf, 0, 8).waitdone()
    assert buf.data(3, 0) == 0
    zone.read(qpair, buf, 16).waitdone()
    assert buf.data(3, 0) == 0

    with zone.ioworker(io_size=8, lba_random=False, read_percentage=0):
        pass
    ret = zone.ioworker(io_size=2, offset_start=0, lba_random=False,
                        read_percentage=0).start().close()
    assert ret.io_count_write == 500


def test_zns_multiple_ioworker(nvme0n1):
    zone1 = Zone(nvme0n1, 0x08000)
    zone2 = Zone(nvme0n1, 0x10000)
    zone3 = Zone(nvme0n1, 0x18000)
    w1 = zone1.ioworker(io_size=3, offset_start=0, io_count=2000).start()
    w2 = zone2.ioworker(io_size=8, offset_start=10, lba_random=False, read_percentage=100).start()
    w3 = zone3.ioworker(io_size=16).start()
    ret1 = w1.close()
    ret2 = w2.close()
    ret3 = w3.close()
    assert ret1.io_count_write == 2000
    assert ret2.io_count_read == 113
    assert ret3.io_count_read == 0
    assert ret3.io_count_write == 4096//16
