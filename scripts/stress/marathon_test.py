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

import nvme as d


TEST_LOOPS = 3  # 3000


@pytest.fixture(scope="function")
def nvme0n1(nvme0):
    # skip crc calc in write
    ret = d.Namespace(nvme0, 1, 1)
    yield ret
    ret.close()

    
def test_ioworker_longtime(nvme0n1, qcount=4, second=100):
    l = []
    io_total = 0
    io_per_second = [list() for i in range(qcount)]
    output_percentile_latency = [dict.fromkeys([99.9])]*qcount

    nvme0n1.format(512)
    
    for i in range(qcount):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=False, qdepth=16,
                             read_percentage=0,
                             output_io_per_second=io_per_second[i],
                             time=second).start()
        l.append(a)

    for i in range(qcount):
        r = l[i].close()
        logging.info(r)
        io_total += (r.io_count_read+r.io_count_nonread)

    logging.info("Q %d IOPS: %.3fK" % (qcount, io_total/second/1000))
    output_iops = [sum(i) for i in zip(*io_per_second)]

    import matplotlib
    matplotlib.use('svg')    
    import matplotlib.pyplot as plt
    plt.figure(figsize=(30, 12))
    plt.plot(output_iops)
    plt.xlabel('second')
    plt.ylabel('#IO')
    plt.xlim(0)
    plt.ylim(0)
    plt.tight_layout()
    plt.savefig("iops.png", dpi=600)
    plt.close()

    
def test_write_and_read_to_eol(nvme0, subsystem, nvme0n1: d.Namespace, verify):
    assert verify
    
    # format drive
    nvme0n1.format(512)
    lba_count = nvme0n1.id_data(7, 0)

    # test for PE cycles
    for i in range(TEST_LOOPS):
        logging.info("loop %d start" % i)

        # write 1 pass of whole drive
        io_size = 64*1024//512  # 64KB
        write_start = time.time()
        nvme0n1.ioworker(io_size=io_size,
                         lba_random=False,
                         read_percentage=0,
                         io_count=lba_count//io_size).start().close()
        write_duration = time.time()-write_start
        logging.info("full drive write %d seconds" % write_duration)
        assert write_duration < 1800

        # power cycle
        subsystem.power_cycle(15)
        nvme0.reset()
        
        # read part of drive
        read_time = 1800-write_duration
        nvme0n1.ioworker(io_size=io_size,
                         lba_random=False,
                         read_percentage=100,
                         time=read_time,
                         region_end=lba_count//100).start().close()
        logging.info("loop %d finish" % i)
        
        # power cycle
        subsystem.power_cycle(15)
        nvme0.reset()

