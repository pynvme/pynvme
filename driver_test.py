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
import nvme  # test double import


tcp_target = b'10.24.48.17'  #b'127.0.0.1'

        
@pytest.mark.parametrize("repeat", range(2))
def test_nvme_tcp_basic(repeat):
    c = d.Controller(tcp_target)
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

    
def test_create_device(nvme0, nvme0n1):
    assert nvme0 is not None


def test_create_device_invalid():
    with pytest.raises(d.NvmeEnumerateError):
        nvme1 = d.Controller(b"00:00.0")


def test_create_device_again(nvme0):
    # """docstring cuts all tests below."""
    with pytest.raises(d.NvmeEnumerateError):
        d.Controller(b"10:00.0")


@pytest.mark.parametrize("shift", range(1, 8))
def test_qpair_different_size(nvme0n1, nvme0, shift):
    size = 1 << shift
    logging.info("create io queue size %d" % size)
    d.Qpair(nvme0, size)
    nvme0.getfeatures(7).waitdone()


def test_two_controllers(nvme0):
    nvme1 = d.Controller(b'03:00.0')
    assert nvme0.id_data(63, 24, str)[:6] != nvme1.id_data(63, 24, str)[:6]
    assert nvme0.id_data(23, 4, str) != nvme1.id_data(23, 4, str)
    

def test_random_seed():
    import random
    assert random.randint(1, 1000000) != random.randint(0, 1000000)
    d.srand(10)
    a = random.randint(1, 1000000)
    d.srand(10)
    b = random.randint(1, 1000000)
    assert a == b
    d.srand(100)
    b = random.randint(1, 1000000)
    assert a != b

    
def test_two_namespace_basic(nvme0n1, nvme0, verify):
    nvme1 = d.Controller(b'03:00.0')
    nvme1n1 = d.Namespace(nvme1)
    nvme0n1.format()
    nvme1n1.format()
    
    logging.info("controller0 namespace size: %d" % nvme0n1.id_data(7, 0))
    logging.info("controller1 namespace size: %d" % nvme1n1.id_data(7, 0))
    assert nvme0n1.id_data(7, 0) != nvme1n1.id_data(7, 0)

    q1 = d.Qpair(nvme0, 32)
    q2 = d.Qpair(nvme1, 64)
    buf = d.Buffer(512)
    buf1 = d.Buffer(512)
    buf2 = d.Buffer(512)

    # test nvme0n1
    nvme0n1.read(q1, buf1, 11, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 0
    assert buf1[504] == 0
    nvme0n1.write(q1, buf, 11, 1).waitdone()
    nvme0n1.read(q1, buf1, 11, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 11
    assert buf1[504] == 1

    # test nvme1n1
    nvme1n1.read(q2, buf2, 11, 1).waitdone()
    #print(buf2.dump())
    assert buf2[0] == 0
    assert buf2[504] == 0
    nvme1n1.write(q2, buf, 11, 1).waitdone()
    nvme1n1.read(q2, buf2, 11, 1).waitdone()
    #print(buf2.dump())
    assert buf2[0] == 11
    assert buf2[504] == 2

    assert buf1[:504] == buf2[:504]
    assert buf1[:] != buf2[:]

    # test nvme0n1 again
    nvme0n1.read(q1, buf1, 11, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 11
    assert buf1[504] == 1
    nvme0n1.write(q1, buf, 11, 1).waitdone()
    nvme0n1.read(q1, buf1, 11, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 11
    assert buf1[504] == 3
    
    nvme0n1.read(q1, buf1, 22, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 0
    assert buf1[504] == 0
    nvme0n1.write(q1, buf, 22, 1).waitdone()
    nvme0n1.read(q1, buf1, 22, 1).waitdone()
    #print(buf1.dump())
    assert buf1[0] == 22
    assert buf1[504] == 4

    nvme0.cmdlog(15)
    nvme1.cmdlog(15)
    q1.cmdlog(15)
    q2.cmdlog(15)

    
def test_two_namespace_ioworkers(nvme0n1, nvme0, verify):
    nvme1 = d.Controller(b'03:00.0')
    nvme1n1 = d.Namespace(nvme1)
    with nvme0n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=1), \
         nvme1n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=1):
        pass


def test_nvme_tcp_ioworker():
    c = d.Controller(tcp_target)
    n = d.Namespace(c, 1)
    n.ioworker(io_size=8, lba_align=8,
               region_start=0, region_end=0x100,
               lba_random=False, qdepth=4,
               read_percentage=50, time=15).start().close()

    
def test_write_and_format(nvme0n1, nvme0):
    with nvme0n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=1):
        pass
    
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()    

    
def test_get_identify_quick(nvme0, nvme0n1):
    logging.info("vid: 0x%x" % nvme0.id_data(1, 0))
    logging.info("namespace size: %d" % nvme0n1.id_data(7, 0))
    logging.info("namespace capacity: %d" % nvme0n1.id_data(15, 8))
    logging.info("namespace utilization: %d" % nvme0n1.id_data(23, 16))
    assert nvme0n1.id_data(7, 0) == nvme0n1.id_data(15, 8)
    assert nvme0.id_data(63, 24, str)[0] != 0


def test_get_identify(nvme0, nvme0n1):
    logging.info("controller data")
    id_buf = d.Buffer(4096, 'identify buffer')
    assert id_buf[0] == 0
    nvme0.identify(id_buf, 0, 1)
    nvme0.waitdone()
    assert id_buf[0] != 0
    assert id_buf[0] == nvme0.id_data(0, 0)

    logging.info("namespace data")
    id_buf = d.Buffer(4096, 'identify buffer')
    assert id_buf[0] == 0
    nvme0.identify(id_buf, 1, 0)
    nvme0.waitdone()
    assert id_buf[0] != 0
    assert id_buf[0] == nvme0n1.id_data(0)
    assert nvme0.id_data(4, 0) != nvme0n1.id_data(4, 0)
    assert nvme0n1.id_data(8, 5) != nvme0n1.id_data(4, 0)
    assert nvme0n1.id_data(7, 0) == nvme0n1.id_data(15, 8)
    assert nvme0n1.id_data(23, 16) == nvme0n1.id_data(15, 8)

    logging.info("active namespace id data")
    id_buf = d.Buffer(4096, 'identify buffer')
    assert id_buf[0] == 0
    nvme0.identify(id_buf, 0, 2)
    nvme0.waitdone()
    assert id_buf[0] != 0

    logging.info("wrong namespace data")
    with pytest.warns(UserWarning, match="ERROR status: 00/0b"):
        nvme0.identify(id_buf, 0, 0).waitdone()

    logging.info("wrong active namespace nsid")
    with pytest.warns(UserWarning, match="ERROR status: 00/0b"):
        nvme0.identify(id_buf, 0xffffffff, 2).waitdone()

    logging.info("wrong namespace nsid")
    with pytest.warns(UserWarning, match="ERROR status: 00/0b"):
        nvme0.identify(id_buf, 0xffffff, 0).waitdone()


def test_get_pcie_config_class_code(nvme0):
    p = d.Pcie(nvme0)
    assert p[9:12] == [2, 8, 1]


def test_get_pcie_registers(pcie):
    vid = pcie.register(0, 2)
    did = pcie.register(2, 2)
    logging.info("vid %x, did %x" % (vid, did))


def test_pcie_capability_d3hot(pcie):
    assert None == pcie.cap_offset(2)

    # get pm register
    assert None != pcie.cap_offset(1)
    pm_offset = pcie.cap_offset(1)
    pmcs = pcie[pm_offset+4]
    logging.info("pmcs %x" % pmcs)

    # set d3hot
    pcie[pm_offset+4] = pmcs|3     #D3hot
    pmcs = pcie[pm_offset+4]
    logging.info("pmcs %x" % pmcs)

    # and exit d3hot
    time.sleep(1)
    pcie[pm_offset+4] = pmcs&0xfc  #D0
    pmcs = pcie[pm_offset+4]
    logging.info("pmcs %x" % pmcs)


def test_get_nvme_register_vs(nvme0):
    cid = nvme0[0x08]
    assert cid == 0x010200 or cid == 0x010100 or cid == 0x010300


def test_get_lba_format(nvme0n1):
    assert nvme0n1.get_lba_format() == nvme0n1.get_lba_format(512, 0)
    assert nvme0n1.get_lba_format(4096, 0) != nvme0n1.get_lba_format(512, 0)
    assert nvme0n1.get_lba_format(4097, 0) == None
    assert nvme0n1.get_lba_format() < 16


def test_enable_and_disable_hmb():
    nvme0 = d.Controller(b'03:00.0')
    
    # setfeatures on hmb
    hmb_size = nvme0.id_data(275, 272)
    hmb_list_buf = d.Buffer(4096)

    if hmb_size == 0:
        pytest.skip("hmb is not supported")

    # for hmb setfeatures commands
    buf = d.Buffer(4096)
    hmb_status = 0
    def cb(cdw0, status):
        nonlocal hmb_status
        hmb_status = cdw0

    # disable hmb
    nvme0.setfeatures(0x0d, 0).waitdone()

    # getfeatures of hmb to check
    nvme0.getfeatures(0x0d, buf=buf, cb=cb).waitdone()
    assert hmb_status == 0

    #one buffer, one entry in the list
    hmb_buf = d.Buffer(4096*hmb_size)
    hmb_list_buf[0:8] = hmb_buf.phys_addr.to_bytes(8, 'little')
    hmb_list_buf[8:12] = hmb_size.to_bytes(4, 'little')

    hmb_list_phys = hmb_list_buf.phys_addr
    nvme0.setfeatures(0x0d, 1, hmb_size,
                      hmb_list_phys&0xffffffff,
                      hmb_list_phys>>32, 1).waitdone()

    # getfeatures of hmb to check
    nvme0.getfeatures(0x0d, buf=buf, cb=cb).waitdone()
    assert hmb_status == 1

    # disable hmb
    nvme0.setfeatures(0x0d, 0).waitdone()

    # getfeatures of hmb to check
    nvme0.getfeatures(0x0d, buf=buf, cb=cb).waitdone()
    assert hmb_status == 0

    # enable
    nvme0.enable_hmb()

    # getfeatures of hmb to check
    nvme0.getfeatures(0x0d, buf=buf, cb=cb).waitdone()
    assert hmb_status == 1

    # disable hmb
    nvme0.disable_hmb()

    # getfeatures of hmb to check
    nvme0.getfeatures(0x0d, buf=buf, cb=cb).waitdone()
    assert hmb_status == 0


def test_write_identify_and_verify(nvme0, nvme0n1):
    id_buf = d.Buffer(4096)
    nvme0.identify(id_buf)
    nvme0.waitdone()
    assert id_buf[0] != 0

    # explict allocate resource when not using fixture
    q = d.Qpair(nvme0, 20)
    n = nvme0n1
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()
    n.write(q, id_buf, 5, 8)
    q.waitdone()
    read_buf = d.Buffer(4096, "read buffer")
    n.read(q, read_buf, 5, 8)
    q.waitdone()
    assert id_buf[:10] == read_buf[:10]

    id_buf[0] += 1
    n.write(q, id_buf, 5, 8).waitdone()
    n.read(q, read_buf, 5, 8).waitdone()
    assert id_buf[:10] == read_buf[:10]
    logging.info("test end")


def test_write_identify_and_verify_with_callback(nvme0, nvme0n1):
    id_buf = d.Buffer(4096)
    nvme0.identify(id_buf).waitdone()

    q = d.Qpair(nvme0, 20)
    n = nvme0n1
    read_buf = d.Buffer(4096, "read buffer")

    def read_cb(cdw0, status):
        assert id_buf[:40] == read_buf[:40]

    def write_cb(cdw0, status):
        n.read(q, read_buf, 5, 8, cb=read_cb)

    n.write(q, id_buf, 5, 8, cb=write_cb).waitdone(2)

    id_buf[0] += 1
    n.write(q, id_buf, 5, 8, cb=write_cb).waitdone(2)
    id_buf[9] = (id_buf[9] >> 1)
    n.write(q, id_buf, 5, 8, cb=write_cb).waitdone(2)


def test_io_waitdone_many_command(nvme0, nvme0n1):
    id_buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    q.waitdone()

    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    q.waitdone()
    q.waitdone()

    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    q.waitdone(2)

    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    q.waitdone(2)
    q.waitdone(3)

    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    q.waitdone(5)

    assert True


def test_write_and_flush(nvme0, nvme0n1):
    id_buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

    nvme0n1.flush(q)
    q.waitdone(1)

    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.flush(q)
    q.waitdone(2)

    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.write(q, id_buf, 5, 8)
    nvme0n1.flush(q)
    q.waitdone(6)


def test_write_zeroes(nvme0, nvme0n1):
    if not nvme0n1.supports(0x08):
        pytest.skip("command not support")

    q = d.Qpair(nvme0, 8)
    buf = d.Buffer(4096)

    buf[0] = 0x5a
    nvme0n1.write(q, buf, 8, 8)
    q.waitdone()
    nvme0n1.read(q, buf, 8, 8)
    q.waitdone()
    assert buf[0] != 0

    nvme0n1.write_zeroes(q, 8, 8)
    q.waitdone()
    nvme0n1.read(q, buf, 8, 8)
    q.waitdone()
    assert buf[0] == 0

    buf[0] = 0x5a
    buf[512*7] = 0x5a
    nvme0n1.write(q, buf, 8, 8)
    q.waitdone()
    nvme0n1.read(q, buf, 8, 8)
    q.waitdone()
    assert buf[0] != 0
    nvme0n1.read(q, buf, 15, 1)
    q.waitdone()
    assert buf[0] != 0

    logging.info("write zeroes 4KB-512, partial 4KB")
    nvme0n1.write_zeroes(q, 8, 7)
    q.waitdone()
    nvme0n1.read(q, buf, 8, 7)
    q.waitdone()
    assert buf[0] == 0
    nvme0n1.read(q, buf, 15, 1)
    q.waitdone()
    assert buf[0] != 0


def test_write_and_compare(nvme0, nvme0n1):
    if not nvme0n1.supports(0x08):
        pytest.skip("command not support")

    q = d.Qpair(nvme0, 8)
    buf = d.Buffer(4096)

    #Check if support compare command
    compare_support = nvme0.id_data(521, 520) & 0x1
    if compare_support == 0:
        pytest.skip("Not support compare command!")

    logging.info("write zeroes and then compare")
    nvme0n1.write_zeroes(q, 0, 8).waitdone()
    nvme0n1.compare(q, buf, 0, 8).waitdone()

    logging.info("write something and compare")
    buf[0] = 77
    nvme0n1.write(q, buf, 0, 8).waitdone()
    nvme0n1.compare(q, buf, 0, 8).waitdone()

    logging.info("read and then compare")
    nvme0n1.read(q, buf, 0, 8).waitdone()
    nvme0n1.compare(q, buf, 0, 8).waitdone()

    logging.info("modify and then compare, should fail")
    with pytest.warns(UserWarning, match="ERROR status: 02/85"):
        buf[0] = 99
        nvme0n1.compare(q, buf, 0, 8).waitdone()


def test_dsm_trim_and_read(nvme0, nvme0n1):
    empty_buf = d.Buffer(4096)
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

    #Check if support compare command
    compare_support = nvme0.id_data(521, 520) & 0x1
    if compare_support == 0:
        pytest.skip("Not support compare command!")

    # write lba 0
    buf[10] = 1
    nvme0n1.write(q, buf, 0, 8).waitdone()

    # verify data, non empty
    logging.info("compare")
    with pytest.warns(UserWarning, match="ERROR status: 02/85"):
        nvme0n1.compare(q, empty_buf, 0, 8).waitdone()

    # trim lba 0
    logging.info("trim lba 0")
    buf.set_dsm_range(0, 0, 8)
    nvme0n1.dsm(q, buf, 1).waitdone()


def test_timeout_command_completion(nvme0, nvme0n1):
    def format_timeout_cb(cdw0, status1):
        # timeout command, cpl all 1
        assert cdw0 == 0xffffffff
        assert status1 == 0xffff
        
    # 512GB DUT format takes long time
    assert nvme0.timeout == 10000
    nvme0.timeout = 10
    with pytest.warns(UserWarning, match="drive timeout:"):
        nvme0.format(nvme0n1.get_lba_format(512, 0), ses=1, cb=format_timeout_cb).waitdone()
    assert nvme0.timeout == 10
    
    def format_non_timeout_cb(cdw0, status1):
        # timeout command, cpl all 1
        assert cdw0 != 0xffffffff
        assert status1 != 0xffff
        
    # 512GB DUT format takes long time
    nvme0.timeout = 15000
    nvme0.format(nvme0n1.get_lba_format(512, 0), ses=1, cb=format_non_timeout_cb).waitdone()
    assert nvme0.timeout == 15000

    # set to default value
    nvme0.timeout = 10000
    
    
def test_set_timeout(nvme0, nvme0n1):
    # 512GB DUT format takes long time
    logging.info("format all namespace")
    assert nvme0.timeout == 10000
    
    nvme0.timeout = 10
    with pytest.warns(UserWarning, match="drive timeout:"):
        nvme0.format(nvme0n1.get_lba_format(512, 0), ses=1).waitdone()
    assert nvme0.timeout == 10

    # timeout is set by controller
    nvme1 = d.Controller(tcp_target)
    nvme1.timeout = 10000
    with pytest.warns(UserWarning, match="drive timeout:"):
        nvme0.format(nvme0n1.get_lba_format(512, 0), ses=1).waitdone()
    assert nvme0.timeout == 10
        
    nvme0.timeout = 15000
    nvme0.format(nvme0n1.get_lba_format(512, 0), ses=1).waitdone()
    
    nvme0.timeout = 100000
    nvme0.reset()
    assert nvme0.timeout == 100000

    # set to default value
    nvme0.timeout = 10000


@pytest.mark.parametrize("lbaf", range(2))
def test_format_basic(nvme0, nvme0n1, lbaf):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

    logging.info("crypto secure erase one namespace")
    with pytest.warns(UserWarning, match="ERROR status:"):
        nvme0.format(nvme0n1.get_lba_format(512, 0), ses=2).waitdone()

    logging.info("invalid format")
    with pytest.warns(UserWarning, match="ERROR status:"):
        nvme0.format(nvme0n1.get_lba_format(512, 0), ses=3).waitdone()

    logging.info("invalid nsid")
    with pytest.warns(UserWarning, match="ERROR status: 00/0b"):
        nvme0.format(nvme0n1.get_lba_format(512, 0), 0, 0).waitdone()
        nvme0n1.read(q, buf, 0, 1).waitdone()

    logging.info("format all namespace")
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()
    nvme0n1.read(q, buf, 1, 1).waitdone()
    assert buf[0] == 0


def test_dsm_deallocate_one_tu(nvme0, nvme0n1):
    buf = d.Buffer(4096)
    read_buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

    logging.info("write init data")
    nvme0n1.write(q, buf, 8, 8).waitdone()
    nvme0n1.read(q, buf, 8, 8).waitdone()
    assert buf[0] != 0
    orig_data = buf[0]

    logging.info("trim and read")
    buf.set_dsm_range(0, 8, 8)
    nvme0n1.dsm(q, buf, 1).waitdone()
    nvme0n1.read(q, buf, 8, 8).waitdone()
    assert buf[0] == 0 or buf[0] == orig_data


@pytest.mark.parametrize("size", [4096, 10, 4096*2])
@pytest.mark.parametrize("offset", [4096, 10, 4096*2])
def test_firmware_download(nvme0, size, offset):
    buf = d.Buffer(size)
    nvme0.fw_download(buf, offset).waitdone()


def test_firmware_commit(nvme0):
    logging.info("commit without valid firmware image")
    with pytest.warns(UserWarning, match="ERROR status: 01/07"):
        nvme0.fw_commit(1, 0).waitdone()

    logging.info("commit to invalid firmware slot")
    with pytest.warns(UserWarning, match="ERROR status: 01/06"):
        nvme0.fw_commit(7, 2).waitdone()


def test_sanitize_basic(nvme0, nvme0n1, verify, buf):
    # check if sanitize is supported
    nvme0.identify(buf).waitdone()
    if buf.data(331, 328) == 0:
        pytest.skip("sanitize operation is not supported")

    # write some daat
    nvme0n1.ioworker(io_size=8, lba_align=8,
                     region_start=0, region_end=256*1024*8, # 1GB space
                     lba_random=False, qdepth=16,
                     read_percentage=0, time=10).start().close()

    # start sanitize, and wait it complete
    logging.info("supported sanitize operation: %d" % buf.data(331, 328))
    nvme0.sanitize().waitdone()

    # aer should happen after sanitize done
    with pytest.warns(UserWarning, match="AER notification is triggered"):
        # sanitize status log page
        nvme0.getlogpage(0x81, buf, 20).waitdone()
        while buf.data(3, 2) & 0x7 != 1:  # sanitize is not completed
            logging.info("sanitize progress %d%%" % (buf.data(1, 0)*100//0xffff))
            nvme0.getlogpage(0x81, buf, 20).waitdone()
            time.sleep(1)
    
    logging.info("verify data after sanitize")
    q = d.Qpair(nvme0, 8)
    nvme0n1.read(q, buf, 11, 1).waitdone()
    assert buf[0] == 0
    assert buf[511] == 0

    # read after sanitize
    nvme0n1.ioworker(io_size=8, lba_align=8,
                     region_start=0, region_end=256*1024*8, # 1GB space
                     lba_random=False, qdepth=16,
                     read_percentage=100, time=10).start().close()

    
@pytest.mark.parametrize("nsid", [0, 1, 0xffffffff])
def test_dst_short(nvme0, nsid):
    nvme0.dst(1, nsid).waitdone()

    # check dst log page till no dst in progress
    buf = d.Buffer(4096)
    nvme0.getlogpage(0x6, buf, 32).waitdone()
    while buf[0]:
        logging.info("current dst progress percentage: %d%%" % buf[1])
        time.sleep(1)
        nvme0.getlogpage(0x6, buf, 32).waitdone()


def test_dst_extended(nvme0):
    nvme0.dst(2).waitdone()

    # check dst log page till no dst in progress
    buf = d.Buffer(4096)
    nvme0.getlogpage(0x6, buf, 32).waitdone()
    while buf[0]:
        logging.info("current dst progress percentage: %d%%" % buf[1])
        time.sleep(1)
        nvme0.getlogpage(0x6, buf, 32).waitdone()


def test_write_uncorrectable(nvme0, nvme0n1):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

    #Check if support write uncorrectable command
    wuecc_support = nvme0.id_data(521, 520) & 0x2
    if wuecc_support == 0:
        pytest.skip("Not support write uncorrectable command!")

    logging.info("read uncorretable")
    nvme0n1.write_uncorrectable(q, 0, 8).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        nvme0n1.read(q, buf, 0, 8).waitdone()

    logging.info("read normal data")
    nvme0n1.write(q, buf, 0, 8).waitdone()
    nvme0n1.read(q, buf, 0, 8).waitdone()

    logging.info("read uncorretable")
    nvme0n1.write_uncorrectable(q, 0, 8).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        nvme0n1.read(q, buf, 0, 8).waitdone()

    logging.info("read normal")
    nvme0n1.write(q, buf, 0, 8)
    q.waitdone()
    nvme0n1.read(q, buf, 0, 8)
    q.waitdone()

    # non-4K uncorretable write
    logging.info("write partial uncorretable")
    nvme0n1.write_uncorrectable(q, 0, 4)
    q.waitdone()

    logging.info("read normal lba")
    nvme0n1.read(q, buf, 6, 2)
    q.waitdone()

    logging.info("read normal lba")
    nvme0n1.read(q, buf, 8, 8)
    q.waitdone()

    logging.info("read uncorretable")
    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        nvme0n1.read(q, buf, 2, 2).waitdone()

    logging.info("read partial uncorretable")
    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        nvme0n1.read(q, buf, 2, 8).waitdone()

    logging.info("read normal")
    nvme0n1.write(q, buf, 0, 8)
    q.waitdone()
    nvme0n1.read(q, buf, 0, 8)
    q.waitdone()


@pytest.mark.parametrize("io_count", [0, 1, 8, 9])
@pytest.mark.parametrize("lba_count", [0, 1, 8, 9])
@pytest.mark.parametrize("lba_offset", [0, 1, 8, 9])
def test_different_io_size_and_count(nvme0, nvme0n1,
                                     lba_offset, lba_count, io_count):
    io_qpair = d.Qpair(nvme0, 10)
    lba_count += 1

    bufs = []
    for i in range(io_count):
        bufs.append(d.Buffer(lba_count*512))

    for i in range(io_count):
        nvme0n1.write(io_qpair, bufs[i], lba_offset, lba_count)
    io_qpair.waitdone(io_count)

    for i in range(io_count):
        nvme0n1.read(io_qpair, bufs[i], lba_offset, lba_count)
    io_qpair.waitdone(io_count)


def test_create_invalid_qpair(nvme0):
    with pytest.raises(d.QpairCreationError):
        q = d.Qpair(nvme0, 20, prio=1)


def test_buffer_data_pattern():
    b = d.Buffer(512, "pattern")
    assert b[0] == 0
    assert b[511] == 0
    
    b = d.Buffer(512, "pattern", 0, 0)
    assert b[0] == 0
    assert b[511] == 0
    
    b = d.Buffer(512, "pattern", 1)
    assert b[0] == 0xff
    assert b[511] == 0xff
    
    b = d.Buffer(512, "pattern", 1, 32)
    assert b[0] == 1
    assert b[511] == 0

    b = d.Buffer(512, "pattern", 0x12345678, 32)
    assert b[0] == 0x78
    assert b[511] == 0x12

    b = d.Buffer(512, "pattern", 0, 0xbeef)
    assert b[0] == 0
    assert b[511] == 0

    b = d.Buffer(512, "pattern", 1, 0xbeef)
    assert b[11] == 0
    assert b[511] == 0
    
    b = d.Buffer(512, "pattern", 10, 0xbeef)
    assert b[511] == 0
    
    b = d.Buffer(512, "pattern", 50, 0xbeef)
    assert b[256] == 0
    assert b[511] == 0

    b = d.Buffer(512, "pattern", 99, 0xbeef)
    assert b[511] == 0

    b = d.Buffer(512, "pattern", 100, 0xbeef)


def test_buffer_access_overflow():
    b = d.Buffer(1000)
    
    b[999] = 0
    assert b[999] == 0

    with pytest.raises(IndexError):
        b[1000] = 0

    with pytest.raises(IndexError):
        assert b[1000] == 0
        
    
def test_buffer_set_get():
    b = d.Buffer()
    b[0] = 0xa5
    b[1] = 0x5a
    b[2] = 0xa5
    assert b[0] == 0xa5
    b[0:10] = b"1234567890"
    assert b[0] == 0x31
    b[0:10:1] = b"1234567890"
    assert b[0] == 0x31
    b[1:10:1] = b"abcd567890"
    assert b[0] == 0x31
    b[:10:1] = b"1234567890"
    assert b[0] == 0x31
    b[:10] = b"1234567890"
    assert b[0] == 0x31
    b[0:] = b"1234567890"
    assert b[0] == 0x31
    b[0] = 0x5a
    assert b[0] == 0x5a
    assert b[0:10] == b"Z234567890"
    assert b[0:10:1] == b"Z234567890"
    assert b[:10:1] == b"Z234567890"
    assert b[:10] == b"Z234567890"
    assert b[:] == b[0::1]
    # this is a full slice
    assert b[0:] != b"Z234567890"


@pytest.mark.parametrize("repeat", range(2))
def test_create_many_qpair(nvme0, repeat):
    ql = []
    for i in range(16):
        ql.append(d.Qpair(nvme0, 8))
    del ql
    
    for i in range(50):
        q = d.Qpair(nvme0, 80)


def test_set_get_features(nvme0):
    nvme0.setfeatures(0x7, cdw11=(16 << 16)+16)
    nvme0.setfeatures(0x7, cdw11=(16 << 16)+16)
    nvme0.waitdone(2)
    nvme0.getfeatures(0x7)
    nvme0.waitdone()
    assert True


def test_pcie_reset(nvme0, pcie):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        ret = buf.data(115, 112)
        logging.info("power cycles: %d" % ret)
        return ret

    powercycle = get_power_cycles(nvme0)
    pcie.reset()
    assert powercycle == get_power_cycles(nvme0)


def test_subsystem_shutdown_notify(nvme0, subsystem):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        return buf.data(115, 112)

    powercycle = get_power_cycles(nvme0)
    logging.info("power cycles: %d" % powercycle)

    subsystem.shutdown_notify()
    nvme0.reset()
    assert powercycle == get_power_cycles(nvme0)

    subsystem.shutdown_notify(True)
    nvme0.reset()
    assert powercycle == get_power_cycles(nvme0)


def test_write_fua_latency(nvme0n1, nvme0):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

    now = time.time()
    for i in range(100):
        nvme0n1.write(q, buf, 0, 8).waitdone()
    non_fua_time = time.time()-now
    logging.info("normal write latency %fs" % non_fua_time)

    now = time.time()
    for i in range(100):
        # write with FUA enabled
        nvme0n1.write(q, buf, 0, 8, 1<<30).waitdone()
    fua_time = time.time()-now
    logging.info("FUA write latency %fs" % fua_time)

    assert non_fua_time < fua_time

    
def test_read_fua_latency(nvme0n1, nvme0):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

    # first time read to load data into SSD buffer
    nvme0n1.read(q, buf, 0, 8).waitdone()

    now = time.time()
    for i in range(10000):
        nvme0n1.read(q, buf, 0, 8).waitdone()
    non_fua_time = time.time()-now
    logging.info("normal read latency %fs" % non_fua_time)

    now = time.time()
    for i in range(10000):
        nvme0n1.read(q, buf, 0, 8, 1<<30).waitdone()
    fua_time = time.time()-now
    logging.info("FUA read latency %fs" % fua_time)


def test_write_limited_retry(nvme0n1, nvme0):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)
    nvme0n1.write(q, buf, 0, 8, 1<<31).waitdone()


def test_read_limited_retry(nvme0n1, nvme0):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)
    nvme0n1.read(q, buf, 0, 8, 1<<31).waitdone()


def test_subsystem_reset():
    nvme1 = d.Controller(b'03:00.0')
    subsystem = d.Subsystem(nvme1)
    
    def get_power_cycles(nvme1):
        buf = d.Buffer(512)
        nvme1.getlogpage(2, buf, 512).waitdone()
        logging.info("power cycles: %d" % buf.data(115, 112))
        return buf.data(115, 112)

    powercycle = get_power_cycles(nvme1)
    subsystem.reset()
    assert powercycle == get_power_cycles(nvme1)


def test_io_qpair_msix_interrupt_all(nvme0, nvme0n1):
    buf = d.Buffer(4096)
    ql = []
    for i in range(16):
        q = d.Qpair(nvme0, 8)
        ql.append(q)
        logging.info("qpair %d" % q.sqid)

        q.msix_clear()
        assert not q.msix_isset()
        nvme0n1.read(q, buf, 0, 8)
        time.sleep(0.1)
        assert q.msix_isset()
        q.waitdone()


def test_io_qpair_msix_interrupt_mask(nvme0, nvme0n1):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

    q.msix_clear()
    assert not q.msix_isset()
    nvme0n1.read(q, buf, 0, 8)
    time.sleep(1)
    assert q.msix_isset()
    q.waitdone()

    q.msix_clear()
    assert not q.msix_isset()
    nvme0n1.read(q, buf, 0, 8)
    time.sleep(1)
    assert q.msix_isset()
    q.waitdone()

    q.msix_clear()
    q.msix_mask()
    assert not q.msix_isset()
    nvme0n1.read(q, buf, 0, 8)
    assert not q.msix_isset()
    time.sleep(1)
    assert not q.msix_isset()
    q.msix_unmask()
    time.sleep(0.1)
    assert q.msix_isset()
    q.waitdone()

    q2 = d.Qpair(nvme0, 8)

    q.msix_clear()
    q2.msix_clear()
    assert not q.msix_isset()
    assert not q2.msix_isset()
    nvme0n1.read(q2, buf, 0, 8)
    time.sleep(1)
    assert not q.msix_isset()
    assert q2.msix_isset()
    q2.waitdone()


def test_io_qpair_msix_interrupt_coalescing(nvme0, nvme0n1):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)
    q.msix_clear()
    assert not q.msix_isset()

    # aggregation time: 100*100us=0.01s, aggregation threshold: 2
    nvme0.setfeatures(8, (200<<8)+10)

    # 1 cmd, check interrupt latency
    nvme0n1.read(q, buf, 0, 8)
    start = time.time()
    while not q.msix_isset(): pass
    latency1 = time.time()-start
    logging.info("interrupt latency %dus" % (latency1*1000000))
    q.waitdone()
    q.msix_clear()

    # 2 cmd, check interrupt latency
    nvme0n1.read(q, buf, 0, 8)
    nvme0n1.read(q, buf, 0, 8)
    start = time.time()
    while not q.msix_isset(): pass
    latency2 = time.time()-start
    logging.info("interrupt latency %dus" % (latency2*1000000))
    q.waitdone(2)
    q.msix_clear()

    # 1 cmd, check interrupt latency
    nvme0n1.read(q, buf, 0, 8)
    start = time.time()
    while not q.msix_isset(): pass
    latency1 = time.time()-start
    logging.info("interrupt latency %dus" % (latency1*1000000))
    q.waitdone()
    q.msix_clear()


def test_ioworker_fast_complete(nvme0n1):
    nvme0n1.ioworker(io_size=64, lba_align=64,
                     lba_random=False, qdepth=64,
                     region_end=512, io_count=128, 
                     read_percentage=0).start().close()


def test_power_cycle_with_ioworker_dirty(nvme0n1, nvme0, subsystem):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        logging.info("power cycles: %d" % buf.data(115, 112))
        logging.info("unsafe shutdowns: %d" % buf.data(159, 144))
        return buf.data(115, 112)

    # read and power cycle
    powercycle = get_power_cycles(nvme0)
    with nvme0n1.ioworker(io_size=256, lba_align=256,
                          lba_random=False, qdepth=64,
                          read_percentage=100, time=5):
        pass
    start_time = time.time()
    subsystem.power_cycle(15)
    init_time_read = time.time()-start_time
    assert get_power_cycles(nvme0) == powercycle+1
    
    # write and power cycle
    powercycle = get_power_cycles(nvme0)
    with nvme0n1.ioworker(io_size=256, lba_align=256,
                          lba_random=False, qdepth=64,
                          read_percentage=0, time=5):
        pass
    start_time = time.time()
    subsystem.power_cycle(15)
    init_time_write = time.time()-start_time
    assert get_power_cycles(nvme0) == powercycle+1

    # init time after dirty write should be longer
    logging.info("read init time %f, write init time %f" %
                 (init_time_read, init_time_write))

    # write and clean power cycle
    powercycle = get_power_cycles(nvme0)
    with nvme0n1.ioworker(io_size=256, lba_align=256,
                          lba_random=False, qdepth=64,
                          read_percentage=0, time=5):
        pass
    subsystem.shutdown_notify()
    start_time = time.time()
    subsystem.power_cycle(15)
    init_time_write_clean = time.time()-start_time
    assert get_power_cycles(nvme0) == powercycle+1

    # dirty init time should be longer than clean init time
    logging.info("clean init time %f, dirty init time %f" %
                 (init_time_write_clean, init_time_write))
    
    
def test_subsystem_power_cycle(nvme0, subsystem):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        logging.info("power cycles: %d" % buf.data(115, 112))
        return buf.data(115, 112)

    import time
    start_time = time.time()
    powercycle = get_power_cycles(nvme0)

    subsystem.power_cycle(15)
    assert get_power_cycles(nvme0) == powercycle+1
    assert time.time()-start_time >= 5


@pytest.mark.parametrize("delay", [0, 10])
def test_subsystem_power_cycle_without_notify(nvme0, nvme0n1, subsystem, delay):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        logging.info("power cycles: %d" % buf.data(115, 112))
        logging.info("unsafe shutdowns: %d" % buf.data(159, 144))
        return buf.data(115, 112)

    import time
    start_time = time.time()
    powercycle = get_power_cycles(nvme0)

    with nvme0n1.ioworker(io_size=256, lba_align=256,
                          lba_random=False, qdepth=64,
                          read_percentage=0, time=15):
        pass

    time.sleep(delay)
    subsystem.power_cycle(15)

    assert powercycle+1 == get_power_cycles(nvme0)


@pytest.mark.parametrize("abrupt", [False, True])
def test_subsystem_power_cycle_with_notify(nvme0, nvme0n1, subsystem, abrupt):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        p = buf.data(127, 112)
        logging.info("power cycles: %d" % p)
        logging.info("unsafe shutdowns: %d" % buf.data(159, 144))
        return p

    import time
    start_time = time.time()
    powercycle = get_power_cycles(nvme0)

    with nvme0n1.ioworker(io_size=256, lba_align=256,
                          lba_random=False, qdepth=64,
                          read_percentage=0, time=10):
        pass

    subsystem.shutdown_notify(abrupt)
    subsystem.power_cycle(15)

    assert powercycle+1 == get_power_cycles(nvme0)


def test_controller_reset(nvme0):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        logging.info("power cycles: %d" % buf.data(115, 112))
        return buf.data(115, 112)

    powercycle = get_power_cycles(nvme0)
    logging.info("power cycles: %d" % powercycle)
    nvme0.reset()
    assert get_power_cycles(nvme0) == powercycle


def test_get_smart_data(nvme0):
    smart_buffer = d.Buffer(4096, "smart data buffer")
    nvme0.getlogpage(0x2, smart_buffer, 512)
    nvme0.waitdone()
    assert smart_buffer[2] == 0 or smart_buffer[2] == 1


def test_abort_aer_commands(nvme0, aer):
    # aer callback function
    def cb(cdw0, status):
        logging.info("in aer cb, status 0x%x" % status)
        assert ((status&0xfff)>>1) == 0x0007
    aer(cb)

    for i in range(100):
        nvme0.abort(i)

    logging.info("reap 104 command, including abort, and also aer commands")
    with pytest.warns(UserWarning, match="AER notification"):
        nvme0.waitdone(104)


def test_ioworker_maximum(nvme0n1):
    wl = []
    start_time = time.time()

    for i in range(16):
        a = nvme0n1.ioworker(io_size=8, lba_align=16,
                             lba_random=False, qdepth=16,
                             read_percentage=100, time=10)
        wl.append(a)

    for w in wl:
        w.start()
    logging.info("started all ioworkers")

    for w in wl:
        w.close()


def test_ioworker_progress(nvme0, nvme0n1):
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()
    with nvme0n1.ioworker(io_size=8, lba_align=16,
                          lba_random=False, qdepth=16,
                          read_percentage=100, time=5) as w:
        for i in range(5):
            time.sleep(1)
            # logging.info(w.progress)  #obsoleted
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()

    
def test_ioworker_simplified(nvme0n1):
    nvme0n1.ioworker(io_size=2, time=2).start().close()

    
def test_ioworker_iosize_inputs(nvme0n1):
    d.srand(0x58e7f337)
    nvme0n1.ioworker(io_size=8, time=1).start().close()
    nvme0n1.ioworker(io_size=[1, 8], time=1).start().close()
    nvme0n1.ioworker(io_size=range(1, 8), time=1).start().close()
    nvme0n1.ioworker(io_size={1: 2, 8: 8}, time=1).start().close()
    nvme0n1.ioworker(io_size={1: 2, 8: 8}, lba_align=[1, 8], time=1).start().close()

    
@pytest.mark.parametrize("repeat", range(20))
def test_ioworker_distribution(nvme0n1, repeat):
    distribution = [0]*100
    distribution[1] = 10000
    nvme0n1.ioworker(io_size=8, lba_align=8,
                     lba_random=True, qdepth=16,
                     distribution = distribution, 
                     read_percentage=0, time=2).start().close()
    
    distribution = [100]*100
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=True, qdepth=64,
                         distribution = distribution, 
                         read_percentage=100, time=10).start().close()
    logging.debug(r)

    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=True, qdepth=64,
                         read_percentage=100, time=10).start().close()
    logging.debug(r)
    
    
def test_ioworker_simplified_context(nvme0n1):
    with nvme0n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=2) as w:
        logging.info("ioworker context start")
    logging.info("ioworker context finish")


def test_ioworker_output_io_per_latency(nvme0n1, nvme0):
    output_percentile_latency = dict.fromkeys([10, 50, 90, 99, 99.9, 99.99, 99.999, 99.99999])
    logging.info(output_percentile_latency)
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=False, qdepth=32,
                         read_percentage=100, time=10,
                         output_percentile_latency=output_percentile_latency).start().close()
    logging.info(output_percentile_latency)
    logging.info(r)
    heavy_latency_average = r.latency_average_us
    max_iops = (r.io_count_read+r.io_count_write)*1000//r.mseconds

    # limit iops, should get smaller latency
    output_percentile_latency = dict.fromkeys([10, 50, 90, 99, 99.9, 99.99, 99.999, 99.99999])
    logging.info(output_percentile_latency)
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=False, qdepth=32,
                         iops=max_iops//2, 
                         read_percentage=100, time=10,
                         output_percentile_latency=output_percentile_latency).start().close()
    logging.info(output_percentile_latency)
    logging.info(r)
    assert r.latency_average_us < heavy_latency_average

    output_io_per_second = []
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=False, qdepth=32,
                         read_percentage=0, time=10,
                         output_io_per_second=output_io_per_second,
                         output_percentile_latency=output_percentile_latency).start().close()
    logging.info(output_io_per_second)
    assert len(output_io_per_second) == 10
    logging.info(output_percentile_latency)
    logging.info(r)
    assert output_percentile_latency[99.999] < output_percentile_latency[99.99999]


def test_ioworker_output_io_per_second(nvme0n1, nvme0):
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()

    output_io_per_second = []
    nvme0n1.ioworker(io_size=8, lba_align=16,
                     lba_random=True, qdepth=16,
                     read_percentage=0, time=7,
                     iops=1234,
                     output_io_per_second=output_io_per_second).start().close()
    logging.info(output_io_per_second)
    assert len(output_io_per_second) == 7
    assert output_io_per_second[0] != 0
    assert output_io_per_second[-1] >= 1233
    assert output_io_per_second[-1] <= 1235

    output_io_per_second = []
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=True, qdepth=16,
                         read_percentage=100, time=10,
                         iops=12345,
                         output_io_per_second=output_io_per_second).start().close()
    logging.info(output_io_per_second)
    logging.info(r)
    assert len(output_io_per_second) == 10
    assert r.iops_consistency != 0


def test_ioworker_output_io_per_second_consistency(nvme0n1, nvme0):
    w = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=True, qdepth=16,
                         read_percentage=0, time=30,
                         output_io_per_second=[]).start()
    w.close()
    assert w.iops_consistency() == w.iops_consistency(99.99)
    assert w.iops_consistency(99.9) == w.iops_consistency(99)
    assert w.iops_consistency(90) != w.iops_consistency(50)

    w = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=True, qdepth=16,
                         read_percentage=0, time=3).start()
    w.close()
    with pytest.raises(AssertionError):
        w.iops_consistency()


@pytest.mark.parametrize('depth', [256, 512, 1023])
def test_ioworker_huge_qdepth(nvme0, nvme0n1, depth):
    # """test huge queue in ioworker"""
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()
    nvme0n1.ioworker(io_size=8, lba_align=16,
                     lba_random=False, qdepth=depth,
                     read_percentage=100, time=5).start().close()


def test_ioworker_fill_driver(nvme0, nvme0n1):
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()
    nvme0n1.ioworker(io_size=256, lba_align=256,            # 128K
                     region_start=0, region_end=256*1024*8, # 1GB space
                     lba_random=False, qdepth=16,
                     read_percentage=0, io_count=1024*8).start().close()


def test_ioworker_deepest_qdepth(nvme0n1):
    nvme0n1.ioworker(io_size=8, lba_align=64,
                     lba_random=False, qdepth=1023,
                     read_percentage=100, time=2).start().close()


@pytest.mark.parametrize("qcount", [1, 2, 4, 8, 16])
def test_ioworker_iops_multiple_queue(nvme0n1, qcount):
    l = []
    io_total = 0
    for i in range(qcount):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             region_start=0, region_end=256*1024*8, # 1GB space
                             lba_random=False, qdepth=16,
                             read_percentage=100, time=10).start()
        l.append(a)

    for a in l:
        r = a.close()
        io_total += (r.io_count_read+r.io_count_write)

    logging.info("Q %d IOPS: %.3fK" % (qcount, io_total/10000))


@pytest.mark.parametrize("qcount", [1, 2, 4, 8, 16])
def test_ioworker_bandwidth_multiple_queue(nvme0n1, qcount):
    l = []
    io_total = 0
    for i in range(qcount):
        a = nvme0n1.ioworker(io_size=256, lba_align=256,
                             region_start=0, region_end=256*1024*8, # 1GB space
                             lba_random=False, qdepth=16,
                             read_percentage=100, time=10).start()
        l.append(a)

    for a in l:
        r = a.close()
        io_total += (r.io_count_read+r.io_count_write)

    logging.info("Q %d: %dMB/s" % (qcount, (128*io_total)/10000))


@pytest.mark.parametrize("qcount", [1, 2, 4, 8, 16])
def test_ioworker_iops_multiple_queue_fob(nvme0, nvme0n1, qcount):
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()
    test_ioworker_iops_multiple_queue(nvme0n1, qcount)

    
def test_ioworker_invalid_qdepth(nvme0, nvme0n1):
    # format to clear all data before test
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()

    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=8, lba_align=64,
                         lba_random=False, qdepth=0,
                         read_percentage=100, time=2).start().close()

    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=8, lba_align=64,
                         lba_random=False, qdepth=1,
                         read_percentage=100, time=2).start().close()

    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=8, lba_align=64,
                         lba_random=False, qdepth=1024,
                         read_percentage=100, time=2).start().close()

    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=8, lba_align=64,
                         lba_random=False, qdepth=5000,
                         read_percentage=100, time=2).start().close()


def test_ioworker_invalid_io_size(nvme0, nvme0n1):
    # format to clear all data before test
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()

    with pytest.warns(UserWarning, match="ioworker host ERROR"):
        nvme0n1.ioworker(io_size=257, lba_align=64,
                         lba_random=False, qdepth=4,
                         read_percentage=100, time=2).start().close()

    with pytest.warns(UserWarning, match="ioworker host ERROR"):
        nvme0n1.ioworker(io_size=0x10000, lba_align=64,
                         lba_random=False, qdepth=4,
                         read_percentage=100, time=2).start().close()


# test error handle of driver, test could continue after failed case
def test_ioworker_iops_confliction(verify, nvme0n1):
    assert verify
    import time
    start_time = time.time()
    ww = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=0,
                          iops=0, io_count=0, time=10,
                          qprio=0, qdepth=16).start()
    wr = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=100,
                          iops=10, io_count=0, time=10,
                          qprio=0, qdepth=16).start()

    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        wr.close()

    report = ww.close()
    assert report.error == 0
    assert time.time()-start_time > 2.0


def test_ioworker_activate_crc32(nvme0n1, verify, nvme0):
    # verify should be enabled
    assert verify

    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()

    r1 = nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=False, qdepth=32,
                          region_end=1000000,
                          read_percentage=100, time=5).start().close()

    # write some valid data first
    w = nvme0n1.ioworker(io_size=256, lba_align=256,
                         lba_random=False, qdepth=32,
                         region_end=1000000,
                         read_percentage=0, time=10).start().close()

    r2 = nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=False, qdepth=32,
                          region_end=1000000,
                          read_percentage=100, time=5).start().close()
    assert r1["io_count_read"] > r2["io_count_read"]


def test_ioworker_iops_confliction_read_write_mix(nvme0n1, verify):
    # rw mixed ioworkers cause verification fail
    assert verify

    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                             lba_random=True,
                             region_start=0, region_end=1000,
                             read_percentage=50,
                             iops=0, io_count=0, time=1,
                             qprio=0, qdepth=16).start().close()


def test_ioworker_iops(nvme0n1):
    import time
    start_time = time.time()
    w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=100,
                         iops=1000, io_count=10000, time=0,
                         qprio=0, qdepth=16)
    w.start()
    report = w.close()
    assert report['io_count_write'] < 1050
    assert report['mseconds'] > 9000
    assert time.time()-start_time > 9
    assert time.time()-start_time < 20


def test_ioworker_time(nvme0n1):
    import time
    start_time = time.time()
    w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=50,
                         iops=10, io_count=10000, time=10,
                         qprio=0, qdepth=4)
    w.start()
    w.close()
    assert time.time()-start_time > 10.0
    assert time.time()-start_time < 12.0


def test_ioworker_io_count(nvme0n1):
    import time
    start_time = time.time()
    w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=50,
                         iops=10, io_count=100, time=100,
                         qprio=0, qdepth=4)
    w.start()
    w.close()
    assert time.time()-start_time > 10.0
    assert time.time()-start_time < 12.0


def test_ioworker_io_random(nvme0n1):
    import time
    start_time = time.time()
    w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=8,
                         lba_random=True,
                         region_start=100, region_end=10000,
                         read_percentage=0,
                         iops=0, io_count=0, time=10,
                         qprio=0, qdepth=4)
    w.start()
    w.close()
    assert time.time()-start_time > 10.0
    assert time.time()-start_time < 12.0


def test_ioworker_io_region(nvme0n1):
    import time
    start_time = time.time()
    w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=8,
                         lba_random=False,
                         region_start=100, region_end=10000,
                         read_percentage=0,
                         iops=0, io_count=0, time=10,
                         qprio=0, qdepth=4)
    w.start()
    w.close()
    assert time.time()-start_time > 10.0
    assert time.time()-start_time < 12.0


def test_ioworker_io_region_2(nvme0n1):
    import time
    start_time = time.time()
    w = nvme0n1.ioworker(lba_start=202, io_size=8, lba_align=8,
                         lba_random=True,
                         region_start=100, region_end=10000,
                         read_percentage=0,
                         iops=0, io_count=0, time=10,
                         qprio=0, qdepth=4)
    w.start()
    w.close()
    assert time.time()-start_time > 10.0
    assert time.time()-start_time < 12.0


def test_ioworker_write_read_verify(nvme0n1, verify):
    w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=8, lba_random=False,
                         region_start=0, region_end=100000, read_percentage=0,
                         iops=0, io_count=100000/8, time=0, qprio=0, qdepth=64).start().close()

    wl = []
    for i in range(4):
        w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=8, lba_random=True,
                             region_start=0, region_end=100000, read_percentage=100,
                             iops=0, io_count=0, time=10, qprio=0, qdepth=64).start()
        wl.append(w)

    for w in wl:
        print(w.close())


def test_single_ioworker(nvme0, nvme0n1):
    w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=100,
                         iops=0, io_count=1000, time=10,
                         qprio=0, qdepth=9)
    w.start()
    w.close()


def test_multiple_ioworkers(nvme0n1):
    workers = []
    for i in range(4):
        w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                             lba_random=False,
                             region_start=0, region_end=1000,
                             read_percentage=0,
                             iops=0, io_count=1000, time=0,
                             qprio=0, qdepth=9)
        workers.append(w.start())
    [w.close() for w in workers]


def test_waitdone_nothing(nvme0, nvme0n1):
    nvme0.waitdone(0)
    qpair = d.Qpair(nvme0, 100)
    qpair.waitdone(0)


@pytest.mark.parametrize("repeat", range(10))
def test_ioworkers_with_pattern(nvme0n1, nvme0, repeat):
    with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=0,
                          iops=0, io_count=1000, time=0,
                          qprio=0, qdepth=9):
        for i in range(100):
            nvme0.getfeatures(7).waitdone()

    with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=0,
                          iops=0, io_count=1000, time=0,
                          qprio=0, qdepth=9), \
        nvme0n1.ioworker(lba_start=1000, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=1000, time=0,
                         qprio=0, qdepth=9), \
        nvme0n1.ioworker(lba_start=8000, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=1000, time=0,
                         qprio=0, qdepth=9), \
        nvme0n1.ioworker(lba_start=8000, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=10, time=0,
                         qprio=0, qdepth=9):
        id_buf = d.Buffer(4096)
        assert id_buf[0] == 0
        nvme0.identify(id_buf)
        nvme0.waitdone()
        assert id_buf[0] != 0


def test_ioworkers_with_many_huge_io(nvme0n1, nvme0):
    nvme0n1.ioworker(lba_start=0, io_size=256, lba_align=64,
                     lba_random=False,
                     region_start=0, region_end=1000,
                     read_percentage=0,
                     iops=0, io_count=10000, time=0,
                     qprio=0, qdepth=9).start().close()
    nvme0n1.ioworker(lba_start=8000, io_size=256, lba_align=64,
                     lba_random=False,
                     region_start=0, region_end=1000,
                     read_percentage=0,
                     iops=0, io_count=10000, time=0,
                     qprio=0, qdepth=9).start().close()
    nvme0n1.ioworker(lba_start=80000, io_size=255, lba_align=64,
                     lba_random=False,
                     region_start=0, region_end=1000,
                     read_percentage=0,
                     iops=0, io_count=10000, time=0,
                     qprio=0, qdepth=9).start().close()


def test_ioworkers_read_and_write_conflict(nvme0n1, nvme0, verify):
    # """read write confliction will cause data mismatch.
    #
    # When the same LBA the read and write commands are operating on, NVMe
    # spec does not garentee the order of read and write operation, so the
    # data of read command got could be old data or the new data of the write
    # command just written.
    # """

    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()
        
    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=8,
                              lba_random=False,
                              region_start=0, region_end=128,
                              read_percentage=0,
                              iops=0, io_count=0, time=2,
                              qprio=0, qdepth=32), \
             nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=8,
                              lba_random=False,
                              region_start=0, region_end=128,
                              read_percentage=100,
                              iops=0, io_count=0, time=2,
                              qprio=0, qdepth=32):
            pass


def test_ioworker_distribution_read_write_confliction(nvme0n1, verify):
    assert verify
    
    distribution = [0]*100
    distribution[1] = 10000
    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        with nvme0n1.ioworker(io_size=8, lba_align=8,
                              lba_random=True, qdepth=64,
                              distribution = distribution, 
                              read_percentage=0, time=60), \
             nvme0n1.ioworker(io_size=8, lba_align=8,
                              lba_random=True, qdepth=64,
                              distribution = distribution, 
                              read_percentage=100, time=60):
            pass

    distribution2 = [0]*100
    distribution2[2] = 10000
    with nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=True, qdepth=64,
                          distribution = distribution, 
                          read_percentage=0, time=60), \
         nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=True, qdepth=64,
                          distribution = distribution2, 
                          read_percentage=100, time=60):
        pass

        
def test_ioworkers_read_and_write(nvme0n1, nvme0):
    # """read write confliction will cause data mismatch.
    #
    # One mitigation solution is separate read and write to differnt IOWorkers
    # and operate different LBA regions to avoid read-write confliction.
    # """

    with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=8,
                          lba_random=False,
                          region_start=0, region_end=128,
                          read_percentage=0,
                          iops=0, io_count=0, time=10,
                          qprio=0, qdepth=32), \
        nvme0n1.ioworker(lba_start=1000, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=128, region_end=256,
                         read_percentage=100,
                         iops=0, io_count=0, time=10,
                         qprio=0, qdepth=32):
        pass


def test_single_large_ioworker(nvme0n1):
    r = nvme0n1.ioworker(lba_start=0, io_size=256, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=1, time=0,
                         qprio=0, qdepth=9).start().close()
    assert r.io_count_write == 1


def test_admin_cmd_log(nvme0):
    nvme0.getfeatures(7).waitdone()
    nvme0.cmdlog(15)

    
def test_io_cmd_log(nvme0, nvme0n1):
    q = d.Qpair(nvme0, 16)
    buf = d.Buffer(512)
    for i in range(5):
        nvme0n1.read(q, buf, 0).waitdone()
    q.cmdlog(15)

    
def test_cmd_cb_features(nvme0):
    orig_config = 0

    # every callback function has to have different names
    def getfeatures_cb_1(cdw0, status):
        nonlocal orig_config; orig_config = cdw0
    nvme0.getfeatures(7, cb=getfeatures_cb_1).waitdone()

    def setfeatures_cb_1(cdw0, status):
        pass
    nvme0.setfeatures(7, orig_config-1, cb=setfeatures_cb_1).waitdone()

    # nesting callbacks: only submit commands in callback, but waitdone() outside of callbacks
    def getfeatures_cb_2(cdw0, status):
        assert cdw0 == orig_config-1
        # cannot call waitdone in callback functions
        nvme0.setfeatures(7, orig_config)
    # call waitdone one more time for setfeatures in above callback
    nvme0.getfeatures(7, cb=getfeatures_cb_2).waitdone(2)

    def getfeatures_cb_3(cdw0, status):
        assert cdw0 == orig_config
    nvme0.getfeatures(7, cb=getfeatures_cb_3).waitdone()


def test_buffer_token_single_process(nvme0, nvme0n1):
    io_qpair = d.Qpair(nvme0, 10)
    b = d.Buffer(512)

    nvme0n1.write(io_qpair, b, 0, 1).waitdone()
    nvme0n1.read(io_qpair, b, 0, 1).waitdone()
    token_begin = b.data(507, 504)

    with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=0,
                          iops=0, io_count=100, time=0,
                          qprio=0, qdepth=9):
        pass

    nvme0n1.write(io_qpair, b, 1, 1).waitdone()
    nvme0n1.read(io_qpair, b, 1, 1).waitdone()
    token_end = b.data(507, 504)
    assert token_end-token_begin == 8*100+1


def test_buffer_token_multi_processes(nvme0, nvme0n1):
    io_qpair = d.Qpair(nvme0, 10)
    b = d.Buffer()

    nvme0n1.write(io_qpair, b, 0, 1).waitdone()
    nvme0n1.read(io_qpair, b, 0, 1).waitdone()
    token_begin = b.data(507, 504)

    with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=0,
                          iops=0, io_count=128, time=0,
                          qprio=0, qdepth=9), \
        nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=128, time=0,
                         qprio=0, qdepth=9):
        pass

    nvme0n1.write(io_qpair, b, 1, 1).waitdone()
    nvme0n1.read(io_qpair, b, 1, 1).waitdone()
    token_end = b.data(507, 504)
    assert token_end-token_begin == 8*128*2+1


def test_buffer_token_single_small_process(nvme0, nvme0n1):
    io_qpair = d.Qpair(nvme0, 10)
    b = d.Buffer()

    nvme0n1.write(io_qpair, b, 0, 1).waitdone()
    nvme0n1.read(io_qpair, b, 0, 1).waitdone()
    token_begin = b.data(507, 504)

    with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=0,
                          iops=0, io_count=1, time=0,
                          qprio=0, qdepth=9):
        pass

    nvme0n1.write(io_qpair, b, 100, 1).waitdone()
    nvme0n1.read(io_qpair, b, 100, 1).waitdone()
    token_end = b.data(507, 504)
    assert token_end-token_begin == 8*1+1


def test_buffer_token_single_large_process(nvme0, nvme0n1):
    io_qpair = d.Qpair(nvme0, 10)
    b = d.Buffer()

    nvme0n1.write(io_qpair, b, 0, 1).waitdone()
    nvme0n1.read(io_qpair, b, 0, 1).waitdone()
    token_begin = b.data(507, 504)

    with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=0,
                          iops=0, io_count=1000, time=0,
                          qprio=0, qdepth=9):
        pass

    nvme0n1.write(io_qpair, b, 0, 1).waitdone()
    nvme0n1.read(io_qpair, b, 0, 1).waitdone()
    token_end = b.data(507, 504)
    assert token_end-token_begin == 8*1000+1


def test_command_supported_and_effect(nvme0, nvme0n1):
    assert nvme0.supports(0)
    assert nvme0n1.supports(0)
    assert not nvme0.supports(0xff)
    assert not nvme0n1.supports(0xff)


def test_pynvme_timeout_command(nvme0, nvme0n1):
    # pynvme driver timeout: admin cmd
    assert nvme0.timeout == 10000
    now = time.time()
    with pytest.raises(TimeoutError):
        nvme0.waitdone()
    assert time.time()-now > 29
    
    # pynvme driver timeout: io cmd
    now = time.time()
    io_qpair = d.Qpair(nvme0, 10)
    b = d.Buffer()
    with pytest.raises(TimeoutError):
        nvme0n1.write(io_qpair, b, 0).waitdone(2)
    assert time.time()-now > 29

        
def test_ioworker_timeout_command(nvme0, nvme0n1):
    now = time.time()
    r = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=1, io_count=1000, time=5,
                         qprio=0, qdepth=2).start().close()
    assert time.time()-now > 5
    assert time.time()-now < 10


def test_reentry_waitdone_io_qpair(nvme0, nvme0n1):
    b = d.Buffer(512)
    q = d.Qpair(nvme0, 10)

    def read_cb(cdw0, status):
        nvme0n1.read(q, b, 1, 1).waitdone()
    with pytest.warns(UserWarning, match="ASSERT: cannot re-entry waitdone()"):
        nvme0n1.read(q, b, 2, 1, cb=read_cb).waitdone()

    def read_cb_2(cdw0, status):
        nvme0n1.read(q, b, 3, 1)
    nvme0n1.read(q, b, 4, 1, cb=read_cb_2).waitdone(3)


def test_ioworker_test_end(nvme0n1):
    import time
    start_time = time.time()
    nvme0n1.ioworker(io_size=8, lba_align=16,
                     lba_random=True, qdepth=16,
                     read_percentage=0, time=2).start().close()
    assert time.time()-start_time < 5.0


def test_admin_generic_cmd(nvme0):
    features_value = 0

    def getfeatures_cb_1(cdw0, status):
        nonlocal features_value; features_value = cdw0
    nvme0.getfeatures(0x7, cb=getfeatures_cb_1).waitdone()

    def getfeatures_cb_2(cdw0, status):
        nonlocal features_value; assert features_value == cdw0
    nvme0.send_cmd(0xa, nsid=1, cdw10=7, cb=getfeatures_cb_2).waitdone()

    with pytest.warns(UserWarning, match="ERROR status: 00/02"):
        nvme0.send_cmd(0xa).waitdone()

    with pytest.warns(UserWarning, match="ERROR status: 00/01"):
        nvme0.send_cmd(0xff).waitdone()


def test_io_generic_cmd(nvme0n1, nvme0):
    q = d.Qpair(nvme0, 8)
    
    # invalid command
    with pytest.warns(UserWarning, match="ERROR status: 00/01"):
        nvme0n1.send_cmd(0xff, q, nsid=1).waitdone()
    # invalid nsid
    with pytest.warns(UserWarning, match="ERROR status: 00/0b"):
        nvme0n1.send_cmd(0x0, q).waitdone()
        
    # flush command
    nvme0n1.send_cmd(0x0, q, nsid=1).waitdone()


def test_ioworker_vscode_showcase(nvme0n1):
    with nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=False,
                          qdepth=16, read_percentage=100,
                          iops=100, time=10), \
         nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=True,
                          qdepth=16, read_percentage=100,
                          iops=1000, time=10), \
         nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=True,
                          qdepth=16, read_percentage=100,
                          time=10), \
         nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=False,
                          qdepth=16, read_percentage=0,
                          iops=10, time=10):
         pass


@pytest.mark.parametrize("start", [1, 7, 8, 10, 16])
@pytest.mark.parametrize("length", [1, 7, 8, 10, 16])
def test_ioworker_address_region_512(nvme0, nvme0n1, start, length):
    nvme0.format().waitdone()

    q = d.Qpair(nvme0, 10)
    b = d.Buffer(512)  # zero buffer
    read_buf = d.Buffer(512)

    with nvme0n1.ioworker(io_size=1, io_count=length,
                          lba_align=1, lba_random=False,
                          region_start=start, region_end=start+length,
                          qdepth=16, read_percentage=0):
        pass

    # verify after ioworker write
    nvme0n1.read(q, read_buf, 0).waitdone()
    assert read_buf[:] == b[:]
    nvme0n1.read(q, read_buf, start-1).waitdone()
    assert read_buf[:] == b[:]
    nvme0n1.read(q, read_buf, start).waitdone()
    assert read_buf[:] != b[:]
    nvme0n1.read(q, read_buf, start+length-1).waitdone()
    assert read_buf[:] != b[:]
    nvme0n1.read(q, read_buf, start+length).waitdone()
    assert read_buf[:] == b[:]
    nvme0n1.read(q, read_buf, start+length+1).waitdone()
    assert read_buf[:] == b[:]


def test_fused_operations(nvme0, nvme0n1):
    q = d.Qpair(nvme0, 10)
    b = d.Buffer()
    
    # compare and write
    nvme0n1.write(q, b, 8).waitdone()
    nvme0n1.compare(q, b, 8).waitdone()

    # fused
    nvme0n1.send_cmd(5|(1<<8), q, b, 1, 8, 0, 0)
    nvme0n1.send_cmd(1|(1<<9), q, b, 1, 8, 0, 0)
    q.waitdone(2)

    # atomic: first cmd should be timeout
    nvme0n1.send_cmd(1|(1<<8), q, b, 1, 8, 0, 0).waitdone()
    nvme0n1.send_cmd(5|(1<<9), q, b, 1, 8, 0, 0).waitdone()

    
@pytest.mark.parametrize("lba_size", [4096, 512])
@pytest.mark.parametrize("repeat", range(2))
def test_write_4k_lba(nvme0, nvme0n1, lba_size, repeat):
    nvme0n1.format(lba_size)

    q = d.Qpair(nvme0, 10)
    zb = d.Buffer()  # zero buffer
    buf = d.Buffer()
    lba_start = 8

    # no data
    nvme0n1.read(q, buf, lba_start).waitdone()
    assert buf[:] == zb[:]

    # write
    nvme0n1.write(q, buf, lba_start, 4096//lba_size).waitdone()

    # verify
    nvme0n1.read(q, buf, lba_start).waitdone()
    assert buf[:] != zb[:]

    # compare
    nvme0n1.compare(q, buf, lba_start).waitdone()
    with pytest.warns(UserWarning, match="ERROR status: 02/85"):
        nvme0n1.compare(q, zb, lba_start).waitdone()

    assert buf[0] == lba_start
    #print(buf.dump())


@pytest.mark.parametrize("start", [8, 16])
@pytest.mark.parametrize("length", [8, 16])
def test_ioworker_address_region_4k(nvme0, nvme0n1, start, length):
    nvme0.format().waitdone()

    q = d.Qpair(nvme0, 10)
    b = d.Buffer()  # zero buffer
    read_buf = d.Buffer()

    with nvme0n1.ioworker(io_size=8, io_count=length,
                          lba_align=8, lba_random=False,
                          region_start=start, region_end=start+length,
                          qdepth=16, read_percentage=0):
        pass

    # verify after ioworker write
    nvme0n1.read(q, read_buf, 0).waitdone()
    assert read_buf[:] == b[:]
    nvme0n1.read(q, read_buf, start-1).waitdone()
    assert read_buf[:] == b[:]
    nvme0n1.read(q, read_buf, start).waitdone()
    assert read_buf[:] != b[:]
    nvme0n1.read(q, read_buf, start+length-1).waitdone()
    assert read_buf[:] != b[:]
    nvme0n1.read(q, read_buf, start+length).waitdone()
    assert read_buf[:] == b[:]
    nvme0n1.read(q, read_buf, start+length+1).waitdone()
    assert read_buf[:] == b[:]


def test_ioworker_stress(nvme0n1):
    for i in range(1000):
        logging.info(i)
        with nvme0n1.ioworker(io_size=8, lba_align=8,
                              lba_random=False, io_count=1,
                              qdepth=16, read_percentage=100):
            pass


@pytest.mark.parametrize("repeat", range(200))
def test_ioworker_stress_multiple_small(nvme0n1, repeat):
    l = []
    for i in range(16):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=True, qdepth=8,
                             read_percentage=100, time=2).start()
        l.append(a)

    for a in l:
        r = a.close()


def test_ioworker_longtime(nvme0, nvme0n1, verify):
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()

    l = []
    for i in range(16):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=True, qdepth=64,
                             read_percentage=100, time=60*60).start()
        l.append(a)

    for a in l:
        r = a.close()


@pytest.mark.parametrize("lba_size", [4096, 512, 4096, 512])
def test_namespace_change_format(nvme0, nvme0n1, lba_size, verify):
    nvme0n1.format(lba_size)
    nvme0n1.ioworker(io_size=8, lba_align=8,
                     lba_random=True, qdepth=16, 
                     read_percentage=100, time=1).start().close()


@pytest.mark.parametrize("lba_size", [4096, 512])
def test_ioworker_longtime_deep(nvme0, nvme0n1, lba_size, verify):
    nvme0n1.format(lba_size)

    l = []
    for i in range(2):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=True, qdepth=1023, 
                             read_percentage=100, time=10*60).start()
        l.append(a)

    for a in l:
        r = a.close()

