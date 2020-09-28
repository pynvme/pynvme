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


TEST_SCALE = 10    #1, 10


# trim
@pytest.mark.parametrize("repeat", range(TEST_SCALE))
@pytest.mark.parametrize("lba_count", [8, 8*1024, 0])  # 4K, 4M, all 
def test_trim_time_one_range(nvme0, nvme0n1, lba_count, repeat, qpair):
    buf = d.Buffer(4096)
    if lba_count == 0:
        lba_count = nvme0n1.id_data(7, 0)  # all lba
    buf.set_dsm_range(0, 0, lba_count)
    
    start_time = time.time()
    nvme0n1.dsm(qpair, buf, 1).waitdone()
    with open("report.csv", "a") as f:
        f.write('%.6f\n' % (time.time()-start_time))


@pytest.mark.parametrize("repeat", range(TEST_SCALE))
@pytest.mark.parametrize("io_size", [1, 8, 64, 512, 4096])  # 4K, 4M, all 
def test_trim_time_all_range_buffer(nvme0, nvme0n1, repeat, io_size, qpair):
    buf = d.Buffer(4096)
    for i in range(4096//16):
        buf.set_dsm_range(i, i*io_size, io_size)
    
    start_time = time.time()
    nvme0n1.dsm(qpair, buf, 1).waitdone()
    with open("report.csv", "a") as f:
        f.write('%.6f\n' % (time.time()-start_time))

    
# format
@pytest.mark.parametrize("repeat", range(TEST_SCALE))
def test_format_time(nvme0n1, repeat):
    start_time = time.time()
    nvme0n1.format()
    with open("report.csv", "a") as f:
        f.write('%.6f\n' % (time.time()-start_time))
