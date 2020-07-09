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


def test_controller_reset_with_hmb(nvme0, nvme0n1, buf):
    nvme0n1.format(512)

    hmb_size = nvme0.id_data(275, 272)
    logging.info(hmb_size)
    hmb_buf = d.Buffer(4096*hmb_size)
    assert hmb_buf
    hmb_list_buf = d.Buffer(4096)
    assert hmb_list_buf
    hmb_list_buf[0:8] = hmb_buf.phys_addr.to_bytes(8, 'little')
    hmb_list_buf[8:12] = hmb_size.to_bytes(4, 'little')
    hmb_list_phys = hmb_list_buf.phys_addr

    for i in range(10):
        logging.info(i)
        with nvme0n1.ioworker(io_size=8,
                              lba_random=False,
                              qdepth=8,
                              read_percentage=0,
                              time=30):
            nvme0.setfeatures(0x0d,
                              cdw11=1,
                              cdw12=hmb_size,
                              cdw13=hmb_list_phys&0xffffffff,
                              cdw14=hmb_list_phys>>32,
                              cdw15=1).waitdone()
            time.sleep(5)
            nvme0.setfeatures(0x0d, cdw11=0).waitdone()
            nvme0.reset()

    logging.info(hmb_buf.dump(64*1024))
    del hmb_buf
    del hmb_list_buf
