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
import zipfile
import logging
import nvme as d


def test_ioworker_jedec_enterprise_workload_512(nvme0n1):
    nvme0n1.format(512)
    distribution = [1000]*5 + [200]*15 + [25]*80
    iosz_distribution = {1: 4,
                         2: 1,
                         3: 1,
                         4: 1,
                         5: 1,
                         6: 1,
                         7: 1,
                         8: 67,
                         16: 10,
                         32: 7,
                         64: 3,
                         128: 3}

    nvme0n1.ioworker(io_size=iosz_distribution,
                     lba_random=True,
                     qdepth=128,
                     distribution=distribution,
                     read_percentage=0,
                     ptype=0xbeef, pvalue=100,
                     time=12*3600).start().close()


def test_ioworker_jedec_enterprise_workload_4k(nvme0n1):
    nvme0n1.format(4096)
    distribution = [1000]*5 + [200]*15 + [25]*80
    iosz_distribution = {1: 77,
                         2: 10,
                         4: 7,
                         8: 3,
                         16: 3}

    nvme0n1.ioworker(io_size=iosz_distribution,
                     lba_random=True,
                     qdepth=128,
                     distribution=distribution,
                     read_percentage=0,
                     ptype=0xbeef, pvalue=100,
                     time=12*3600).start().close()

    # change back to 512B LBA format
    nvme0n1.format(512)


def test_replay_jedec_client_trace(nvme0, nvme0n1, qpair):
    mdts = min(nvme0.mdts, 64*1024)  # upto 64K IO
    buf = d.Buffer(mdts, "write", 100, 0xbeef)
    trim_buf_list = [d.Buffer() for i in range(1024)]
    batch = 0
    counter = 0

    nvme0n1.format(512)

    with zipfile.ZipFile("scripts/stress/MasterTrace_128GB-SSD.zip") as z:
        for s in z.open("Client_128_GB_Master_Trace.txt"):
            l = str(s)[7:-5]

            if l[0] == 'h':
                # flush
                nvme0n1.flush(qpair)
                counter += 1
            else:
                op, slba, nlba = l.split()
                slba = int(slba)
                nlba = int(nlba)
                if op == 'e':
                    # write
                    while nlba:
                        n = min(nlba, mdts//512)
                        nvme0n1.write(qpair, buf, slba, n)
                        counter += 1
                        slba += n
                        nlba -= n
                elif op == 's':
                    # trims
                    trim_buf = trim_buf_list[counter]
                    trim_buf.set_dsm_range(0, slba, nlba)
                    nvme0n1.dsm(qpair, trim_buf, 1)
                    counter += 1
                else:
                    logging.error(l)

            # reap in batch for better efficiency
            if counter >= 64:
                qpair.waitdone(counter)
                if batch % 1000 == 0:
                    logging.info("replay progress: %d" % (batch//1000))
                batch += 1
                counter = 0

    qpair.waitdone(counter)
