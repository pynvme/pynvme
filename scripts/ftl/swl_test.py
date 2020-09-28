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


def test_swl_only(nvme0: d.Controller, nvme0n1: d.Namespace, verify):
    import matplotlib.pyplot as plt
    
    logging.info("format")
    nvme0n1.format(512)

    io_size = 128
    ns_size = nvme0n1.id_data(7, 0)
    io_count = ns_size//io_size
    logging.info("fill whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=0).start().close()
    
    io_per_second = []
    logging.info("write hot sequential data")
    # 10GB seq write
    nvme0n1.ioworker(io_size=8,
                     lba_random=False,
                     region_end=10*1024*1024*1024//512, #10GB
                     read_percentage=0,
                     time=10*3600,
                     output_io_per_second=io_per_second).start().close()
    logging.info(io_per_second)

    logging.info("verify whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=100).start().close()

    plt.plot(io_per_second)
    plt.ylim(bottom=0)
    plt.xlim(left=0)
    plt.show()
    

def test_swl_with_gc(nvme0: d.Controller, nvme0n1: d.Namespace, verify):
    import matplotlib.pyplot as plt
    
    logging.info("format")
    nvme0n1.format(512)

    io_size = 128
    ns_size = nvme0n1.id_data(7, 0)
    io_count = ns_size//io_size
    logging.info("fill whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=0).start().close()
    
    distribution = [0]*100
    for i in [0, 3, 11, 28, 60, 71, 73, 88, 92, 98]:
        distribution[i] = 1000
    io_per_second = []
    logging.info("write hot random data")
    r = nvme0n1.ioworker(io_size=8,
                     lba_random=True,
                     distribution = distribution,
                     read_percentage=0,
                     time=10*3600,
                     output_io_per_second=io_per_second).start().close()
    logging.info(io_per_second)
    logging.info(r)

    logging.info("verify whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=100).start().close()

    plt.plot(io_per_second)
    plt.ylim(bottom=0)
    plt.show()
    
