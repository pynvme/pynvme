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


import pytest
import nvme as d

import time
import logging


rand = True
seq = False
TEST_SCALE = 100    #100, 10


def do_fill_drive(rand, nvme0n1, region_end):
    io_size = 8 if rand else 128
    ns_size = nvme0n1.id_data(7, 0)
    io_count = ns_size//io_size
    io_per_second = []
    
    nvme0n1.ioworker(io_size=io_size, lba_align=io_size,
                     lba_random=rand, qdepth=512,
                     region_end=region_end,
                     io_count=io_count, read_percentage=0,
                     output_io_per_second=io_per_second).start().close()
    logging.info(io_per_second)

    
# full drive seq write
def test_clean_and_fill_drive(nvme0n1):
    nvme0n1.format(512)
    do_fill_drive(seq, nvme0n1, nvme0n1.id_data(7, 0))


# random write 20% region to steady
def test_random_write_small_region(nvme0n1):
    do_fill_drive(rand, nvme0n1, nvme0n1.id_data(7, 0)//5)

    
# iops: read/write/mixed
# latency: read/write/mixed
@pytest.mark.parametrize("readp", [100, 90, 67, 50, 33, 10, 0])
def test_steady_iops_latency(nvme0n1, readp):
    percentile_latency = dict.fromkeys([50, 90, 99, 99.9, 99.999])
    io_per_second = []

    w = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=rand, qdepth=64,
                         region_end=nvme0n1.id_data(7, 0)//5, 
                         time=TEST_SCALE, read_percentage=readp,
                         output_percentile_latency=percentile_latency, 
                         output_io_per_second=io_per_second).start()
    r = w.close()
    logging.info(io_per_second)
    consistency = w.iops_consistency(90)
    logging.info(percentile_latency)
    max_iops = (r.io_count_read+r.io_count_nonread)*1000//r.mseconds
    logging.info(max_iops)

    with open("report.csv", "a") as f:
        f.write('%d\n' % readp)
        f.write('%.2f\n' % (consistency/100))
        f.write('%d\n' % percentile_latency[99.9])
        f.write('%d\n' % max_iops)
        
    # latency against iops
    for iops_percentage in [20, 40, 60, 80, 100]:
        iops = max_iops*iops_percentage//100
        w = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=rand, qdepth=64,
                             iops=iops, 
                             region_end=nvme0n1.id_data(7, 0)//5, 
                             time=TEST_SCALE, read_percentage=readp,
                             output_percentile_latency=percentile_latency).start()
        r = w.close()
        logging.info("iops %d, latency %dus" % (iops, r.latency_average_us))

        # write to report
        with open("report.csv", "a") as f:
            f.write('%d\n' % iops)
            f.write('%d\n' % r.latency_average_us)
