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


import os
import time
import pytest
import logging
import warnings

import nvme as d


@pytest.fixture(scope="function")
def tcp(pciaddr):
    ret = d.Tcp('127.0.0.1')
    yield ret
    ret.close()


@pytest.mark.parametrize("repeat", range(2))
def test_nvme_tcp_basic(repeat, tcp):
    c = d.Controller(tcp)
    logging.info("debug: %s" % c.id_data(63, 24, str))
    logging.info("debug: %s" % c.id_data(63, 24, str))
    logging.info("debug: %s" % c.id_data(63, 24, str))

    logging.info("debug: %s" % c.id_data(63, 24, str))
    logging.info("debug: %s" % c.id_data(63, 24, str))
    logging.info("MDTS = %d" % c.mdts)
    logging.info("debug: %s" % c.id_data(63, 24, str))
    logging.info("debug: %s" % c.id_data(63, 24, str))
    assert c.mdts == 128*1024
    c.cmdlog(10)

    
def test_nvme_tcp_ioworker(tcp):
    c = d.Controller(tcp)
    n = d.Namespace(c, 1)
    n.ioworker(io_size=8, lba_align=8,
               region_start=0, region_end=0x100,
               lba_random=False, qdepth=4,
               read_percentage=50, time=15).start().close()
    n.close()
    
    
def test_two_controllers(nvme0, tcp):
    nvme1 = d.Controller(tcp)
    assert nvme0.id_data(63, 24, str)[:6] != nvme1.id_data(63, 24, str)[:6]
    assert nvme0.id_data(23, 4, str) != nvme1.id_data(23, 4, str)


def test_two_namespace_basic(nvme0n1, nvme0, verify, tcp):
    nvme1 = d.Controller(tcp)
    nvme1n1 = d.Namespace(nvme1)
    q1 = d.Qpair(nvme0, 32)
    q2 = d.Qpair(nvme1, 64)
    buf = d.Buffer(512)
    buf1 = d.Buffer(512)
    buf2 = d.Buffer(512)

    nvme0n1.write_zeroes(q1, 11, 1).waitdone()
    nvme0n1.write_zeroes(q1, 22, 1).waitdone()
    nvme1n1.write_zeroes(q2, 11, 1).waitdone()

    logging.info("controller0 namespace size: %d" % nvme0n1.id_data(7, 0))
    logging.info("controller1 namespace size: %d" % nvme1n1.id_data(7, 0))
    assert nvme0n1.id_data(7, 0) != nvme1n1.id_data(7, 0)

    # test nvme0n1
    nvme0n1.read(q1, buf1, 11, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 0
    assert buf1[504] == 0
    nvme0n1.write(q1, buf, 11, 1).waitdone()
    nvme0n1.read(q1, buf1, 11, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 11

    # test nvme1n1
    nvme1n1.read(q2, buf2, 11, 1).waitdone()
    #print(buf2.dump())
    assert buf2[0] == 0
    assert buf2[504] == 0
    nvme1n1.write(q2, buf, 11, 1).waitdone()
    nvme1n1.read(q2, buf2, 11, 1).waitdone()
    #print(buf2.dump())
    assert buf2[0] == 11
    assert buf1[:] != buf2[:]

    # test nvme0n1 again
    nvme0n1.read(q1, buf1, 11, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 11
    nvme0n1.write(q1, buf, 11, 1).waitdone()
    nvme0n1.read(q1, buf1, 11, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 11

    nvme0n1.read(q1, buf1, 22, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 0
    assert buf1[504] == 0
    nvme0n1.write(q1, buf, 22, 1).waitdone()
    nvme0n1.read(q1, buf1, 22, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 22

    nvme0.cmdlog(15)
    nvme1.cmdlog(15)
    q1.cmdlog(15)
    q2.cmdlog(15)

    nvme1n1.close()
    q1.delete()
    q2.delete()

    
def test_two_namespace_ioworkers(nvme0n1, nvme0, verify, tcp):
    nvme1 = d.Controller(tcp)
    nvme1n1 = d.Namespace(nvme1)
    with nvme0n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=1), \
         nvme1n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=1):
        pass

    nvme1n1.close()

