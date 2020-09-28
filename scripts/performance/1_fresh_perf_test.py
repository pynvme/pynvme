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

import logging


rand = True
seq = False

read = True
write = False

def do_ioworker(rand, read, ns):
    """ run ioworkers for basic io performance tests"""
    
    seconds = 10
    io_size = 8 if rand else 128 # 4K or 64K
    rp = 100 if read else 0 # read or write

    r = ns.ioworker(io_size=io_size, lba_align=io_size,
                    region_end=(1<<30)//512, # 1GB space
                    lba_random=rand, qdepth=512,
                    read_percentage=rp, time=seconds).start().close()

    io_total = r.io_count_read+r.io_count_nonread
    iops = io_total//seconds

    return iops if rand else iops*io_size*512  # return Bps for seq IO


def do_fill_drive(rand, nvme0n1):
    io_size = 8 if rand else 128
    ns_size = nvme0n1.id_data(7, 0)
    io_count = ns_size//io_size
    io_per_second = []
    
    r = nvme0n1.ioworker(io_size=io_size, lba_align=io_size,
                         lba_random=rand, qdepth=512,
                         io_count=io_count, read_percentage=0,
                         output_io_per_second=io_per_second).start().close()

    if not rand:
        return [iops*io_size*512 for iops in io_per_second]
    else:
        return io_per_second


def test_create_report_file(nvme0, nvme0n1, pcie):
    orig_timeout = nvme0.timeout
    nvme0.timeout = 100000
    
    nvme0n1.format(512)  # 512 sector size
    
    nvme0.timeout = orig_timeout

    import libpci
    vid = pcie.register(0, 2)
    vendor = libpci.LibPCI().lookup_vendor_name(vid)
    
    model = nvme0.id_data(63, 24, str)
    fw = nvme0.id_data(71, 64, str)
    capacity = str(nvme0n1.id_data(7, 0)*512)
    hmb = nvme0.id_data(275, 272) * 4
    
    qpairs = 0
    def getfeatures_cb(cdw0, status):
        nonlocal qpairs; qpairs = cdw0
        qpairs = (cdw0&0xffff)+1
    nvme0.getfeatures(7, cb=getfeatures_cb).waitdone()
    
    with open("report.csv", "w+") as f:
        f.write("%s\n" % vendor)
        f.write("%s\n" % model)
        f.write("%s\n" % fw)
        f.write("%s\n" % capacity)
        f.write("%d\n" % hmb)
        f.write("%d\n" % qpairs)
    

# empty read
def test_empty_read_performance(nvme0n1):
    logging.info(do_ioworker(seq, read, nvme0n1))
    logging.info(do_ioworker(rand, read, nvme0n1))

    
# write/read in 1GB, cdm
def test_1gb_read_write_performance(nvme0n1):
    with open("report.csv", "a") as f:
        f.write("%d\n" % do_ioworker(seq, write, nvme0n1))
        f.write("%d\n" % do_ioworker(seq, read, nvme0n1))
        f.write("%d\n" % do_ioworker(rand, write, nvme0n1))
        f.write("%d\n" % do_ioworker(rand, read, nvme0n1))


# full drive seq write
def test_fill_drive_first_pass(nvme0n1):
    io_per_sec = do_fill_drive(seq, nvme0n1)
    io_per_sec = io_per_sec[:300]
    with open("report.csv", "a") as f:
        for iops in io_per_sec:
            f.write('%d\n' % iops)
        for i in range(300):
            f.write('0\n')
    
# random
def test_fill_drive_random(nvme0n1, nvme0):
    io_per_sec = do_fill_drive(rand, nvme0n1)
    io_per_sec = io_per_sec[:600]
    with open("report.csv", "a") as f:
        for iops in io_per_sec:
            f.write('%d\n' % iops)
            
        # add temperature, °C
        import pytemperature
        logpage_buf = d.Buffer(512)
        nvme0.getlogpage(2, logpage_buf).waitdone()
        t = round(pytemperature.k2c(logpage_buf.data(2, 1)))
        logging.info(t)
        f.write('%d\n' % t)

        
# 2-pass full drive seq write
@pytest.mark.parametrize("repeat", range(2))
def test_fill_drive_after_random(nvme0n1, repeat):
    io_per_sec = do_fill_drive(seq, nvme0n1)
    io_per_sec = io_per_sec[:600]
    with open("report.csv", "a") as f:
        for iops in io_per_sec:
            f.write('%d\n' % iops)
