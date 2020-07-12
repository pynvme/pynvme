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
    def __init__(self, zns, slba, size, capacity):
        self._slba = slba
        self._size = size
        self._capacity = capacity
        self._ns = zns

    def write(self, qpair, buf, offset, lba_count=1, io_flags=0, 
              dword13=0, dword14=0, dword15=0, cb=None):
        return self._ns.write(qpair, buf, self._slba+offset, lba_count,
                              io_flags, dword13, dword14, dword15, cb)

    def read(self, qpair, buf, offset, lba_count=1, io_flags=0, 
             dword13=0, dword14=0, dword15=0, cb=None):
        return self._ns.read(qpair, buf, self._slba+offset, lba_count,
                             io_flags, dword13, dword14, dword15, cb)

    def ioworker(self, io_size=8, lba_step=None, lba_align=None,
                 lba_random=True, read_percentage=100,
                 op_percentage=None, time=0, qdepth=64,
                 iops=0, io_count=0, offset_start=0, qprio=0,
                 distribution=None, ptype=0xbeef, pvalue=100,
                 io_sequence=None,
                 output_io_per_second=None,
                 output_percentile_latency=None,
                 output_cmdlog_list=None):
        # by default, fill the whole zone
        if time == 0 and io_count == 0 and type(io_size) == int:
            io_count = self._capacity//io_size
            
        return self._ns.ioworker(io_size=io_size,
                                 lba_step=lba_step,
                                 lba_align=lba_align,
                                 lba_random=lba_random,
                                 read_percentage=read_percentage,
                                 op_percentage=op_percentage,
                                 time=time,
                                 qdepth=qdepth,
                                 region_start=self._slba,
                                 region_end=self._slba+self._size,
                                 iops=iops,
                                 io_count=io_count,
                                 lba_start=offset_start+self._slba,
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
    zone = Zone(nvme0n1, 1024, 1024, 1000)
    nvme0n1.write(qpair, buf, 0, 8).waitdone()
    zone.write(qpair, buf, 0, 8).waitdone()
    zone.write(qpair, buf, 8, 8).waitdone()
    nvme0n1.read(qpair, buf, 1024, 8).waitdone()
    assert buf.data(3, 0) == 1024
    zone.read(qpair, buf, 16).waitdone()
    assert buf.data(3, 0) == 0
    
    with zone.ioworker(io_size=8, offset_start=0):
        pass
    ret = zone.ioworker(io_size=2, offset_start=0, lba_random=False,
                        read_percentage=0).start().close()
    assert ret.io_count_write == 500


def test_zns_multiple_ioworker(nvme0n1):
    zone1 = Zone(nvme0n1, 1024, 1024, 1000)
    zone2 = Zone(nvme0n1, 2048, 1024, 900)
    w1 = zone1.ioworker(io_size=2, offset_start=0, io_count=2000).start()
    w2 = zone2.ioworker(io_size=2, offset_start=0).start()
    ret1 = w1.close()
    ret2 = w2.close()
    assert ret1.io_count_read == 2000
    assert ret2.io_count_read == 450

    
