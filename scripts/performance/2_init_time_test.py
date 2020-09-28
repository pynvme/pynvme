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


TEST_SCALE = 10  #10, 1


def do_power_cycle(dirty, subsystem, nvme0n1, nvme0):
    if not dirty:
        # notify drive for a clean shutdown
        start_time = time.time()
        subsystem.shutdown_notify()
        logging.info("notify time %.6f sec" % (time.time()-start_time))

    # boot again
    csv_start = time.time()
    start_time = time.time()
    subsystem.power_cycle(10)
    nvme0.reset()
    logging.info("init time %.6f sec" % (time.time()-start_time-10))

    # first read time
    start_time = time.time()
    q = d.Qpair(nvme0, 16)
    b = d.Buffer(512)
    lba = nvme0n1.id_data(7, 0) - 1
    nvme0n1.read(q, b, lba).waitdone()
    logging.info("media ready time %.6f sec" % (time.time()-start_time))
    q.delete()
    
    # report to csv
    ready_time = time.time()-csv_start-10
    with open("report.csv", "a") as f:
        f.write('%.6f\n' % ready_time)

    
# rand write clean boot time
@pytest.mark.parametrize("repeat", range(TEST_SCALE))
@pytest.mark.parametrize("dirty", [False, True])
def test_boot_time_rand(nvme0, nvme0n1, subsystem, repeat, dirty):
    # write to make drive dirty
    with nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=True, qdepth=64,
                          read_percentage=0, time=TEST_SCALE):
        pass

    do_power_cycle(dirty, subsystem, nvme0n1, nvme0)

    
# seq write clean boot time
@pytest.mark.parametrize("repeat", range(TEST_SCALE))
@pytest.mark.parametrize("dirty", [False, True])
def test_boot_time_seq(nvme0, nvme0n1, subsystem, repeat, dirty):
    # write to make drive dirty
    with nvme0n1.ioworker(io_size=128, lba_align=128,
                          lba_random=False, qdepth=64,
                          read_percentage=0, time=TEST_SCALE):
        pass
    
    do_power_cycle(dirty, subsystem, nvme0n1, nvme0)
