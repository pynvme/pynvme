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
import ping3
import pytest
import logging
import warnings

import nvme as d
import nvme  # test double import


@pytest.mark.parametrize("repeat", range(2))
def test_init_nvme_back_compatibility(pciaddr, repeat):
    pcie = d.Pcie(pciaddr)
    nvme0 = d.Controller(pcie)
    logging.info(hex(pcie.register(0, 4)))
    nvme0n1 = d.Namespace(nvme0, 1)
    nvme0n1.format(512)

    with nvme0n1.ioworker(time=1), \
         nvme0n1.ioworker(time=1):
        pass
    nvme0n1.close()
    pcie.close()


@pytest.mark.parametrize("repeat", range(2))
def test_init_nvme_customerized(pcie, repeat):
    def nvme_init(nvme0):
        # 1. disable cc.en and wait csts.rdy to 0
        nvme0[0x14] = 0
        while not (nvme0[0x1c]&0x1) == 0: pass

        # 2. set admin queue registers
        nvme0.init_adminq()

        # 3. set register cc
        nvme0[0x14] = 0x00460000

        # 4. enable cc.en
        nvme0[0x14] = 0x00460001

        # 5. wait csts.rdy to 1
        while not (nvme0[0x1c]&0x1) == 1: pass

        # 6. identify controller
        nvme0.identify(d.Buffer(4096)).waitdone()

        # 7. create and identify all namespaces
        nvme0.init_ns()

        # 8. set/get num of queues
        nvme0.setfeatures(0x7, cdw11=0x00ff00ff).waitdone()
        nvme0.init_queues(nvme0.getfeatures(0x7).waitdone())

        # 9. send out all aer
        aerl = nvme0.id_data(259)+1
        for i in range(aerl):
            nvme0.aer()

    # initialize pcie registers
    pcie.aspm = 0

    # create controller with user defined init process
    nvme0 = d.Controller(pcie, nvme_init_func=nvme_init)
    aerl = nvme0.id_data(259)+1

    # test with ioworker
    nvme0n1 = d.Namespace(nvme0, 1)
    qpair = d.Qpair(nvme0, 10)
    subsystem = d.Subsystem(nvme0)
    with nvme0n1.ioworker(time=1):
        pass

    # ABORTED - BY REQUEST (00/07)
    with pytest.warns(UserWarning, match="ERROR status: 00/07"):
        for i in range(100):
            nvme0.abort(127-i).waitdone()

    for i in range(aerl):
        nvme0.aer()

    # ABORTED - BY REQUEST (00/07)
    with pytest.warns(UserWarning, match="ERROR status: 00/07"):
        for i in range(10):
            nvme0.abort(127-i).waitdone()

    for i in range(aerl):
        nvme0.aer()

    # ABORTED - BY REQUEST (00/07)
    with pytest.warns(UserWarning, match="ERROR status: 00/07"):
        for i in range(10):
            nvme0.abort(127-i).waitdone()
        qpair.delete()
        
    nvme0.reset()
    nvme0n1.ioworker(time=1).start().close()
    nvme0n1.close()

    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    pcie.reset()               # PCIe reset: hot reset, TS1, TS2
    nvme0.reset()              # reset controller after pcie reset
    nvme0.getfeatures(7).waitdone()

    subsystem.reset()          # NVMe subsystem reset: NSSR
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    subsystem.power_cycle(10)  # power cycle NVMe device: cold reset
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    subsystem.poweroff()
    subsystem.poweron()
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()


def test_jsonrpc_list_qpairs(pciaddr):
    import json
    import socket

    # create the jsonrpc client
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect('/var/tmp/pynvme.sock')

    def jsonrpc_call(sock, method, params=[]):
        # create and send the command
        req = {}
        req['id'] = 1234567890
        req['jsonrpc'] = '2.0'
        req['method'] = method
        req['params'] = params
        sock.sendall(json.dumps(req).encode('ascii'))

        # receive the result
        resp = json.loads(sock.recv(4096).decode('ascii'))
        assert resp['id'] == 1234567890
        assert resp['jsonrpc'] == '2.0'
        return resp['result']

    # no active controller
    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 0

    # create controller and namespace
    pcie = d.Pcie(pciaddr)
    nvme0 = d.Controller(pcie)

    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 1
    assert result[0]['qid']-1 == 0

    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 1
    assert result[0]['qid']-1 == 0

    q1 = d.Qpair(nvme0, 8)
    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 2
    assert result[0]['qid']-1 == 0
    assert result[1]['qid']-1 == 1

    q2 = d.Qpair(nvme0, 8)
    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 3
    assert result[0]['qid']-1 == 0
    assert result[1]['qid']-1 == 1
    assert result[2]['qid']-1 == 2

    nvme0n1 = d.Namespace(nvme0, 1, 1024)
    with nvme0n1.ioworker(io_size=8, time=2):
        time.sleep(1)
        result = jsonrpc_call(sock, 'list_all_qpair')
        assert len(result) == 4
        assert result[0]['qid']-1 == 0
        assert result[1]['qid']-1 == 1
        assert result[2]['qid']-1 == 2
        assert result[3]['qid']-1 == 3

    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 3
    assert result[0]['qid']-1 == 0
    assert result[1]['qid']-1 == 1
    assert result[2]['qid']-1 == 2

    q1.delete()
    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 2
    assert result[0]['qid']-1 == 0
    assert result[1]['qid']-1 == 2

    q2.delete()
    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 1
    assert result[0]['qid']-1 == 0

    nvme0n1.close()
    pcie.close()


def test_expected_dut(nvme0):
    logging.info("0x%x" % nvme0.id_data(1, 0))
    logging.info("0x%x" % nvme0.id_data(3, 2))
    logging.info(nvme0.id_data(63, 24, str))
    logging.info(nvme0.id_data(71, 64, str))
    assert nvme0.id_data(1, 0) == 0x14a4
    assert "CAZ-82256-Q11" in nvme0.id_data(63, 24, str)


def test_read_fua_latency(nvme0n1, nvme0, qpair, buf):
    # first time read to load data into SSD buffer
    nvme0n1.read(qpair, buf, 0, 8).waitdone()

    now = time.time()
    for i in range(10000):
        nvme0n1.read(qpair, buf, 0, 8).waitdone()
    non_fua_time = time.time()-now
    logging.info("normal read latency %fs" % non_fua_time)

    now = time.time()
    for i in range(10000):
        nvme0n1.read(qpair, buf, 0, 8, 1<<14).waitdone()
    fua_time = time.time()-now
    logging.info("FUA read latency %fs" % fua_time)


@pytest.mark.parametrize("repeat", range(2))
def test_false(nvme0, subsystem, repeat):
    assert False


def test_enable_verify_with_large_namespace(nvme0):
    # create namespace with full space verify, but memory is not enough
    nvme0n1 = d.Namespace(nvme0)
    assert nvme0n1.verify_enable() == True
    nvme0n1.verify_enable(False)
    nvme0n1.close()


def test_power_and_reset(pcie, nvme0, subsystem):
    pcie.aspm = 2              # ASPM L1
    pcie.power_state = 3       # PCI PM D3hot
    pcie.aspm = 0
    pcie.power_state = 0

    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    pcie.reset()               # PCIe reset: hot reset, TS1, TS2
    nvme0.reset()              # reset controller after pcie reset
    nvme0.getfeatures(7).waitdone()

    pcie.flr()                 # PCIe function level reset
    nvme0.reset()              # reset controller after pcie reset
    nvme0.getfeatures(7).waitdone()

    subsystem.reset()          # NVMe subsystem reset: NSSR
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    subsystem.power_cycle(10)  # power cycle NVMe device: cold reset
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    subsystem.poweroff()
    subsystem.poweron()
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    
def test_quarch_defined_poweron_poweroff(nvme0):
    import quarchpy

    def poweron():
        logging.info("power off by quarch")
        pwr = quarchpy.quarchDevice("SERIAL:/dev/ttyUSB0")
        pwr.sendCommand("run:power up")
        pwr.closeConnection()

    def poweroff():
        logging.info("power on by quarch")
        pwr = quarchpy.quarchDevice("SERIAL:/dev/ttyUSB0")
        pwr.sendCommand("signal:all:source 7")
        pwr.sendCommand("run:power down")
        pwr.closeConnection()

    s = d.Subsystem(nvme0, poweron, poweroff)


def test_system_defined_poweron_poweroff(nvme0, nvme0n1):
    # no callback provided, fallback to S3 power_cycle
    s = d.Subsystem(nvme0)
    s.poweroff()
    s.poweron()
    nvme0.reset()
    test_hello_world(nvme0, nvme0n1, True)


def test_hello_world(nvme0, nvme0n1, verify):
    assert verify

    # prepare data buffer and IO queue
    read_buf = d.Buffer(512)
    write_buf = d.Buffer(512)
    write_buf[10:21] = b'hello world'
    qpair = d.Qpair(nvme0, 10)

    # send write and read command
    def write_cb(cdw0, status1):  # command callback function
        nvme0n1.read(qpair, read_buf, 0, 1)
    nvme0n1.write(qpair, write_buf, 0, 1, cb=write_cb)

    # wait commands complete and verify data
    assert read_buf[10:21] != b'hello world'
    qpair.waitdone(2)
    assert read_buf[10:21] == b'hello world'
    nvme0n1.compare(qpair, read_buf, 0).waitdone()
    qpair.delete()


def test_create_device(nvme0, nvme0n1):
    assert nvme0 is not None


def test_create_device_invalid():
    with pytest.raises(d.NvmeEnumerateError):
        nvme1 = d.Controller(d.Pcie("0000:00:00.0"))


def test_create_device_again(nvme0):
    with pytest.raises(d.NvmeEnumerateError):
        d.Controller(d.Pcie("0000:10:00.0"))


def test_qpair_overflow(nvme0, nvme0n1, buf):
    q = d.Qpair(nvme0, 4)
    nvme0n1.read(q, buf, 0, 8)
    nvme0n1.read(q, buf, 8, 8)
    nvme0n1.read(q, buf, 16, 8)
    with pytest.raises(AssertionError):
        nvme0n1.read(q, buf, 24, 8)
    q.waitdone(3)
    

@pytest.mark.parametrize("shift", range(1, 8))
def test_qpair_different_size(nvme0n1, nvme0, shift):
    size = 1 << shift
    logging.info("create io queue size %d" % size)
    q = d.Qpair(nvme0, size)
    nvme0.getfeatures(7).waitdone()
    q.delete()


def test_latest_cid(nvme0, nvme0n1, qpair, buf):
    def aer_aborted(cpl):
        logging.info("aer aborted")
    nvme0.aer(cb=aer_aborted)

    with pytest.warns(UserWarning, match="ERROR status: 00/07"):
        nvme0.abort(nvme0.latest_cid).waitdone()

    nvme0n1.read(qpair, buf, 0, 8)
    nvme0.abort(qpair.latest_cid).waitdone()
    qpair.waitdone()

    nvme0n1.read(qpair, buf, 0, 8).waitdone()
    nvme0.abort(qpair.latest_cid).waitdone()


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


def test_controller_reset_redo(nvme0):
    nvme0.reset()
    nvme0.reset()
    nvme0.reset()
    nvme0.reset()
    cdw0 = nvme0.getfeatures(7).waitdone()
    assert cdw0 == 0xf000f

    
def test_ioworker_is_running(nvme0n1):
    with nvme0n1.ioworker(io_size=8, time=6) as a:
        for i in range(5):
            time.sleep(1)
            assert a.running == True
    assert a.running == False

    a = nvme0n1.ioworker(io_size=8, time=1)
    b = nvme0n1.ioworker(io_size=8, time=10)
    assert a.running == True
    assert b.running == True
    logging.info("PASS")
    
    b.start()
    a.start()
    assert a.running == True
    assert b.running == True
    logging.info("PASS")

    time.sleep(2)
    assert a.running == False
    logging.info("PASS")
    assert b.running == True
    logging.info("PASS")

    a.close()
    assert a.running == False
    assert b.running == True
    logging.info("PASS")

    while b.running: pass
    assert a.running == False
    logging.info("PASS")

    b.close()
    assert a.running == False
    assert b.running == False
    logging.info("PASS")


def test_ioworker_last_truncated_io(nvme0n1):
    cmdlog_list = [None]*6
    nvme0n1.ioworker(io_size=8,
                     lba_random=False,
                     io_count=6,
                     region_end=40,
                     qdepth=2,
                     output_cmdlog_list=cmdlog_list).start().close()
    assert cmdlog_list[5][0] == 0
    assert cmdlog_list[5][1] == 8

    nvme0n1.ioworker(io_size=8,
                     lba_random=False,
                     io_count=6,
                     region_end=41,
                     qdepth=2,
                     output_cmdlog_list=cmdlog_list).start().close()
    assert cmdlog_list[5][0] == 40
    assert cmdlog_list[5][1] == 1
    
    
def test_ioworker_sequential_unfixed_iosize(nvme0n1):
    cmdlog_list = [None]*1000
    io_size_list = [1, 3, 8, 30, 64, 100, 128, 200, 256]
    nvme0n1.ioworker(io_size=io_size_list,
                     lba_align=[1]*len(io_size_list),
                     lba_random=False,
                     io_count=len(cmdlog_list),
                     qdepth=2,
                     output_cmdlog_list=cmdlog_list).start().close()
    for i in range(len(cmdlog_list)-1):
        assert cmdlog_list[i][0]+cmdlog_list[i][1] == cmdlog_list[i+1][0]

    nvme0n1.ioworker(io_size=7,
                     lba_align=1, 
                     lba_random=False,
                     io_count=len(cmdlog_list),
                     qdepth=2,
                     output_cmdlog_list=cmdlog_list).start().close()
    for i in range(len(cmdlog_list)-1):
        assert cmdlog_list[i][0]+cmdlog_list[i][1] == cmdlog_list[i+1][0]


def test_ioworker_with_admin(nvme0, nvme0n1, buf, qpair):
    with nvme0n1.ioworker(io_size=256, lba_random=False, read_percentage=100, time=10):
        start_time = time.time()
        while time.time()-start_time < 8:
            nvme0.getlogpage(0x02, buf, 512).waitdone()
            nvme0.identify(buf).waitdone()
            
    with nvme0n1.ioworker(io_size=256, lba_random=False, read_percentage=100, time=10):
        start_time = time.time()
        while time.time()-start_time < 15:
            nvme0.getfeatures(7).waitdone()

    with nvme0n1.ioworker(io_size=256, lba_random=False, read_percentage=100, time=10), \
         nvme0n1.ioworker(io_size=256, lba_random=False, read_percentage=100, time=10), \
         nvme0n1.ioworker(io_size=256, lba_random=False, read_percentage=100, time=10):
        start_time = time.time()
        while time.time()-start_time < 15:
            nvme0.getlogpage(0x02, buf, 512).waitdone()

    with nvme0n1.ioworker(io_size=256, lba_random=False, read_percentage=100, time=10), \
         nvme0n1.ioworker(io_size=256, lba_random=False, read_percentage=100, time=10), \
         nvme0n1.ioworker(io_size=256, lba_random=False, read_percentage=100, time=10):
        start_time = time.time()
        qpair3 = d.Qpair(nvme0, 10)
        while time.time()-start_time < 15:
            nvme0n1.read(qpair3, buf, 0, 8).waitdone()
        qpair3.delete()

    
def test_ioworker_region_smaller_than_iosize(nvme0n1):
    cmdlog_list = [None]*1000
    nvme0n1.ioworker(io_size=128,
                     region_end=100,
                     lba_random=False,
                     io_count=len(cmdlog_list),
                     output_cmdlog_list=cmdlog_list).start().close()
    logging.debug(cmdlog_list)
    for c in cmdlog_list:
        assert c[0] == 0
        assert c[1] == 100
        assert c[2] == 2

    nvme0n1.ioworker(io_size=128,
                     region_end=100,
                     lba_random=True,
                     io_count=len(cmdlog_list),
                     output_cmdlog_list=cmdlog_list).start().close()
    logging.debug(cmdlog_list)
    for c in cmdlog_list:
        assert c[0]+c[1] == 100
        assert c[2] == 2
    

def test_ioworker_sequential_region_unaligned_with_iosize(nvme0n1):
    cmdlog_list = [None]*1000
    nvme0n1.ioworker(io_size=128,
                     lba_random=False,
                     region_end=129,
                     io_count=len(cmdlog_list),
                     output_cmdlog_list=cmdlog_list).start().close()
    for c in cmdlog_list:
        if c[0] == 0:
            assert c[1] == 128
        else:
            assert c[0] == 128
            assert c[1] == 1
    
    
def test_ioworker_sequential_region_fill(nvme0n1):
    cmdlog_list = [None]*11
    nvme0n1.ioworker(io_size=8,
                     lba_random=False,
                     qdepth=2,
                     region_end=77,
                     output_cmdlog_list=cmdlog_list).start().close()
    assert cmdlog_list[0][2] == 0
    assert cmdlog_list[1][1] == 8
    assert cmdlog_list[10][0] == 72
    assert cmdlog_list[10][1] == 5

    nvme0n1.ioworker(io_size=8,
                     lba_align=1,
                     lba_random=False,
                     region_start=1,
                     region_end=77,
                     qdepth=2,
                     output_cmdlog_list=cmdlog_list).start().close()
    assert cmdlog_list[0][2] == 0
    assert cmdlog_list[1][0] == 1
    assert cmdlog_list[1][1] == 8
    assert cmdlog_list[10][0] == 73
    assert cmdlog_list[10][1] == 4
    
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=[8, 64, 128], lba_random=False, region_end=1000).start().close()
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=8,
                         lba_random=False,
                         qdepth=2,
                         output_cmdlog_list=cmdlog_list).start().close()
    
    
def test_ioworker_input_out_of_range(nvme0n1):
    nvme0n1.ioworker(io_size=128, region_end=200, time=1).start().close()
    nvme0n1.ioworker(io_size=128, region_end=200, qdepth=2, io_count=2).start().close()
    nvme0n1.ioworker(io_size=128, region_end=300, time=1).start().close()
    nvme0n1.ioworker(io_size=8, region_end=100, time=1).start().close()
    nvme0n1.ioworker(io_size=range(8, 32, 16), region_end=100, time=1).start().close()
    nvme0n1.ioworker(io_size=128, region_end=100, time=1).start().close()
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=range(8, 128, 8), region_end=100, time=1).start().close()
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=[8, 64, 128], region_end=100, time=1).start().close()
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size={1:1, 128:1}, region_end=100, time=1).start().close()
    nvme0n1.ioworker(io_size=128, region_end=300, time=1).start().close()
    nvme0n1.ioworker(io_size=range(8, 64, 16), region_end=100, time=1).start().close()
    nvme0n1.ioworker(io_size=128, region_end=200, time=1).start().close()
    nvme0n1.ioworker(io_size=128, region_end=256, time=1).start().close()
    nvme0n1.ioworker(io_size=128, region_start=128, region_end=256, time=1).start().close()
    nvme0n1.ioworker(io_size=128, region_end=128, time=1).start().close()
    nvme0n1.ioworker(io_size=128, region_end=256, time=1).start().close()
    nvme0n1.ioworker(io_size=64, region_end=100, time=1).start().close()
    nvme0n1.ioworker(io_size=8, region_end=1024, time=1).start().close()


def test_ioworker_power_cycle_async_cmdlog(nvme0, nvme0n1, subsystem):
    cmdlog_list = [None]*11
    with nvme0n1.ioworker(io_size=8, time=10, iops=2,
                          qdepth=2, lba_random=False,
                          output_cmdlog_list=cmdlog_list):
        time.sleep(5)
        subsystem.power_cycle(10)
        nvme0.reset()

    logging.info(cmdlog_list)
    assert cmdlog_list[0][1] == 0
    assert cmdlog_list[10][0] < 110
    assert cmdlog_list[10][0] == 72
    assert cmdlog_list[10][2] == 2
    assert cmdlog_list[10][0] == cmdlog_list[9][0]+8


@pytest.mark.parametrize("nlba", [1, 2, 8])
@pytest.mark.parametrize("nlba_verify", [10, 100, 100*1024*1024*1024//512])
def test_namespace_nlba_verify(nvme0, nlba, nlba_verify, qpair):
    nvme0n1 = d.Namespace(nvme0, 1, nlba_verify)
    buf = d.Buffer()

    for lba in (0, 9, 10, 11, 150*1024*1024*1024//512):
        nvme0n1.write(qpair, buf, lba, nlba).waitdone()
        nvme0n1.read(qpair, buf, lba, nlba).waitdone()

    assert True == nvme0n1.verify_enable()

    for lba in (0, 9, 10, 11, 150*1024*1024*1024//512):
        nvme0n1.write(qpair, buf, lba, nlba).waitdone()
        nvme0n1.read(qpair, buf, lba, nlba).waitdone()

    nvme0n1.verify_enable(False)
    nvme0n1.close()


def test_ioworker_activate_crc32(nvme0n1, verify, nvme0):
    # verify should be enabled
    assert verify

    nvme0n1.format(512)

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


def test_identify_with_small_buffer(nvme0):
    buf = d.Buffer(512, "part of identify")
    with pytest.raises(AssertionError):
        nvme0.identify(buf).waitdone()

    buf = d.Buffer(3000, "part of identify")
    with pytest.raises(AssertionError):
        nvme0.identify(buf).waitdone()

    buf = d.Buffer(4096, "part of identify")
    nvme0.identify(buf).waitdone()

    buf = d.Buffer(4096*2, "part of identify")
    nvme0.identify(buf).waitdone()


def test_get_pcie_config_class_code(pcie):
    assert pcie[9:12] == [2, 8, 1]


def test_get_pcie_registers(pcie):
    vid = pcie.register(0, 2)
    did = pcie.register(2, 2)
    logging.info("vid %x, did %x" % (vid, did))


def test_pcie_capability_d3hot(pcie, nvme0n1):
    assert None == pcie.cap_offset(2)

    # get pm register
    assert None != pcie.cap_offset(1)
    pm_offset = pcie.cap_offset(1)
    pmcs = pcie[pm_offset+4]
    logging.info("curent power state: %d" % pcie.power_state)

    # set d3hot
    pcie.power_state = 3
    logging.info("curent power state: %d" % pcie.power_state)
    time.sleep(1)

    # and exit d3hot
    pcie.power_state = 0
    logging.info("curent power state: %d" % pcie.power_state)
    nvme0n1.ioworker(io_size=2, time=2).start().close()

    # again
    pcie.power_state = 0
    logging.info("curent power state: %d" % pcie.power_state)
    nvme0n1.ioworker(io_size=2, time=2).start().close()
    assert pcie.power_state == 0


def test_get_nvme_register_vs(nvme0):
    cid = nvme0[0x08]
    assert cid == 0x010200 or cid == 0x010100 or cid == 0x010300


def test_power_cycle_and_format(nvme0, nvme0n1, subsystem):
    subsystem.power_cycle()
    nvme0.reset()
    nvme0n1.format(512)

    subsystem.power_cycle()
    nvme0.reset()
    nvme0n1.ioworker(read_percentage=100, io_count=1).start().close()
    nvme0n1.format(512)


def test_get_lba_format(nvme0n1):
    assert nvme0n1.get_lba_format() == nvme0n1.get_lba_format(512, 0)
    assert nvme0n1.get_lba_format(4096, 0) != nvme0n1.get_lba_format(512, 0)
    assert nvme0n1.get_lba_format(4097, 0) == None
    assert nvme0n1.get_lba_format() < 16


@pytest.mark.parametrize("ps", [4, 3, 2, 1, 0])
def test_format_at_power_state(nvme0, nvme0n1, ps):
    nvme0.setfeatures(0x2, cdw11=ps).waitdone()
    assert nvme0n1.format(ses=0) == 0
    assert nvme0n1.format(ses=1) == 0
    p = nvme0.getfeatures(0x2).waitdone()
    assert p == ps


def test_write_identify_and_verify(nvme0n1, nvme0):
    id_buf = d.Buffer(4096)
    nvme0.identify(id_buf)
    nvme0.waitdone()
    assert id_buf[0] != 0

    nvme0n1.format(512)

    # explict allocate resource when not using fixture
    q = d.Qpair(nvme0, 20)
    n = nvme0n1

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
    q.delete()


def test_callback_with_whole_cpl(nvme0, nvme0n1, buf, qpair):
    f1 = 0
    def cb1(cpl):
        nonlocal f1; f1 = cpl[0]
        logging.info(cpl)
        assert cpl[1] == 0
    nvme0.getfeatures(7, cb=cb1).waitdone()

    def cb2(cpl):
        logging.info(cpl)
        assert cpl[0] == 0
        assert cpl[1] == 0
        assert len(cpl) == 4
        assert type(cpl) is tuple
    nvme0n1.read(qpair, buf, 0, cb=cb2).waitdone()

    a1 = 0
    def cb1(cdw0, status):
        nonlocal a1; a1 = cdw0
        logging.info("in 2nd cb1")
    nvme0.getfeatures(7, cb=cb1).waitdone()
    assert a1 == f1

    def cb3(cdw0, status, third):
        pass
    with pytest.warns(UserWarning, match="ASSERT: command callback"):
        nvme0.getfeatures(7, cb=cb3).waitdone()


def test_multiple_callbacks(nvme0):
    a1 = 0
    def cb1(cdw0, status):
        nonlocal a1; a1 = 1
    nvme0.getfeatures(7, cb=cb1)

    a2 = 0
    def cb2(cdw0, status):
        nonlocal a2; a2 = 2
    nvme0.getfeatures(7, cb=cb2)

    nvme0.waitdone(2)
    assert a1 == 1
    assert a2 == 2


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
    q.delete()


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
    q.delete()
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
    q.delete()


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
    q.delete()


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
    # a dedicated wrong status catch
    with pytest.warns(UserWarning, match="ERROR status: 02/85"):
        buf[0] = 99
        nvme0n1.compare(q, buf, 0, 8).waitdone()

    q.delete()


def test_dsm_trim_and_read(nvme0, nvme0n1, verify):
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

    nvme0n1.read(q, buf, 0, 8).waitdone()
    nvme0n1.compare(q, buf, 0, 8).waitdone()

    q.delete()


def test_wrong_warns(pcie, nvme0, nvme0n1, subsystem, qpair):
    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        nvme0.getfeatures(7).waitdone()
    with pytest.warns(UserWarning, match="AER notification is triggered"):
        nvme0.getfeatures(7).waitdone()


def test_ioworker_pcie_reset_async(nvme0, nvme0n1, pcie):
    for i in range(3):
        logging.info(i)
        start_time = time.time()
        with nvme0n1.ioworker(io_size=8, time=100):
            time.sleep(5)
            pcie.reset()
            nvme0.reset()
        # terminated by power cycle
        assert time.time()-start_time < 25

    with nvme0n1.ioworker(io_size=8, time=10):
        pass
    pcie.reset()
    nvme0.reset()


def _test_ioworker_pcie_flr_reset_async(nvme0, nvme0n1, pcie):
    for i in range(3):
        logging.info(i)
        start_time = time.time()
        with nvme0n1.ioworker(io_size=8, time=100):
            time.sleep(5)
            pcie.flr()
            nvme0.reset()
        # terminated by power cycle
        assert time.time()-start_time < 25

    with nvme0n1.ioworker(io_size=8, time=10):
        pass
    pcie.flr()
    nvme0.reset()
    

def test_ioworker_subsystem_reset_async(nvme0, nvme0n1, subsystem):
    for i in range(3):
        logging.info(i)
        start_time = time.time()
        with nvme0n1.ioworker(io_size=8, time=100):
            time.sleep(5)
            subsystem.reset()
            nvme0.reset()
        # terminated by power cycle
        assert time.time()-start_time < 25

    subsystem.reset()
    nvme0.reset()
    with nvme0n1.ioworker(io_size=8, time=10):
        pass


def test_ioworker_controller_reset_async(nvme0n1, nvme0):
    for i in range(10):
        start_time = time.time()
        with nvme0n1.ioworker(io_size=8, time=100):
            time.sleep(3)
            nvme0.reset()
        # terminated by power cycle
        assert time.time()-start_time < 10

    with nvme0n1.ioworker(io_size=8, time=10):
        pass
    nvme0.reset()


def test_controller_reset_with_ioworkers(nvme0):
    nvme0n1 = d.Namespace(nvme0, 1, 1024*1024)

    for loop in range(10):
        logging.info(loop)
        with nvme0n1.ioworker(io_size=1, time=100), \
             nvme0n1.ioworker(io_size=1, time=100), \
             nvme0n1.ioworker(io_size=1, time=100), \
             nvme0n1.ioworker(io_size=1, time=100), \
             nvme0n1.ioworker(io_size=1, time=100), \
             nvme0n1.ioworker(io_size=1, time=100), \
             nvme0n1.ioworker(io_size=1, time=100), \
             nvme0n1.ioworker(io_size=1, time=100):
            time.sleep(5)
            nvme0.reset()

    nvme0n1.close()


def test_ioworker_power_cycle_async(nvme0, nvme0n1, subsystem):
    for i in range(2):
        start_time = time.time()
        with nvme0n1.ioworker(io_size=8, time=100), \
             nvme0n1.ioworker(io_size=8, time=100), \
             nvme0n1.ioworker(io_size=8, time=100):
            time.sleep(5)
            subsystem.power_cycle(10)
            nvme0.reset()

        # terminated by power cycle
        assert time.time()-start_time < 30

    subsystem.power_cycle(10)
    nvme0.reset()
    with nvme0n1.ioworker(io_size=8, time=10):
        pass


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
    with pytest.warns(UserWarning, match="ERROR status: 01/0a"):
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
    q.delete()


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
    q.delete()


@pytest.mark.parametrize("size", [4096, 10, 4096*2])
@pytest.mark.parametrize("offset", [4096, 10, 4096*2])
def test_firmware_download_overlap(nvme0, size, offset):
    buf = d.Buffer(size)
    #with pytest.warns(UserWarning, match="ERROR status: 01/14"):
    nvme0.fw_download(buf, offset).waitdone()


def test_firmware_download(nvme0, buf):
    for i in range(10):
        nvme0.fw_download(buf, 4096*i).waitdone()


def test_firmware_commit(nvme0):
    logging.info("commit without valid firmware image")
    with pytest.warns(UserWarning, match="ERROR status: 01/07"):
        nvme0.fw_commit(1, 0).waitdone()

    logging.info("commit to invalid firmware slot")
    with pytest.warns(UserWarning, match="ERROR status: 01/06"):
        nvme0.fw_commit(7, 2).waitdone()


def test_sanitize_operations_basic(nvme0, nvme0n1, buf, subsystem):
    if nvme0.id_data(331, 328) == 0:  #L9
        pytest.skip("sanitize operation is not supported")  #L10

    logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))
    nvme0.sanitize().waitdone() 

    # check sanitize status in log page
    with pytest.warns(UserWarning, match="AER notification is triggered"):
        nvme0.getlogpage(0x81, buf, 20).waitdone()  #L17
        while buf.data(3, 2) & 0x7 != 1:  #L18
            time.sleep(1)
            nvme0.getlogpage(0x81, buf, 20).waitdone()  #L20
            progress = buf.data(1, 0)*100//0xffff
            logging.info("%d%%" % progress)

    # check sanitize status
    nvme0.getlogpage(0x81, buf, 20).waitdone()
    assert buf.data(3, 2) & 0x7 == 1


def test_sanitize_operations_powercycle(nvme0, nvme0n1, buf, subsystem):
    if nvme0.id_data(331, 328) == 0:  #L9
        pytest.skip("sanitize operation is not supported")  #L10

    logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))

    # slow down the sanitize
    nvme0.setfeatures(0x2, cdw11=2).waitdone()
    nvme0.sanitize().waitdone()  #L13

    subsystem.power_cycle()
    nvme0.reset()

    # check sanitize status in log page
    with pytest.warns(UserWarning, match="AER notification is triggered"):
        nvme0.getlogpage(0x81, buf, 20).waitdone()  #L17
        while buf.data(3, 2) & 0x7 != 1:  #L18
            time.sleep(1)
            nvme0.getlogpage(0x81, buf, 20).waitdone()  #L20
            progress = buf.data(1, 0)*100//0xffff
            logging.info("%d%%" % progress)

    # check sanitize status
    nvme0.getlogpage(0x81, buf, 20).waitdone()
    assert buf.data(3, 2) & 0x7 == 1

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
    nvme0.setfeatures(0x2, cdw11=0).waitdone()
    q.delete()


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
    q.delete()


def test_write_uncorrectable_unaligned(nvme0, nvme0n1):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)

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
    q.delete()


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
    io_qpair.delete()


def test_send_cmd_exceed_queue(nvme0, nvme0n1, buf):
    nvme0n1.format(512)

    with pytest.raises(AssertionError):
        qpair = d.Qpair(nvme0, 1025)

    logging.info("create queue")
    qpair = d.Qpair(nvme0, 128)
    count = 128 # queue full
    for i in range(count-1):
        nvme0n1.read(qpair, buf, i, 1)
    with pytest.raises(AssertionError):
        nvme0n1.read(qpair, buf, 128, 1)
    qpair.waitdone(127)
    qpair.delete()


@pytest.mark.parametrize("qdepth", [128, 512, 1024])
def test_send_all_slots(nvme0, nvme0n1, buf, qdepth):
    qpair = d.Qpair(nvme0, qdepth)
    for i in range(qdepth-1):
        nvme0n1.read(qpair, buf, i, 1)
    qpair.waitdone(qdepth-1)
    qpair.delete()


def test_send_many_admin(nvme0):
    # 1 more is used by AER
    count = 126
    for i in range(count):
        nvme0.setfeatures(7, cdw11=0xf000f)
    nvme0.waitdone(count)


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


def test_ioworker_data_pattern(nvme0, nvme0n1, qpair):
    nvme0n1.format(512)

    buf = d.Buffer(512)

    r = nvme0n1.ioworker(io_size=8,
                     lba_random=False,
                     read_percentage=0,
                     lba_start=0,
                     io_count=1,
                     pvalue=0x55555555,
                     ptype=32).start().close()
    logging.info(r)
    assert r.io_count_read == 0
    assert r.io_count_write == 1
    assert r.io_count_nonread == 1
    
    nvme0n1.read(qpair, buf, 0).waitdone()
    assert buf[8] == 0x55
    #print(buf.dump(128))

    nvme0n1.ioworker(io_size=8,
                     lba_random=False,
                     read_percentage=0,
                     lba_start=0,
                     io_count=32,
                     qdepth=16,
                     pvalue=0x55555555,
                     ptype=32).start().close()
    for i in range(32*8):
        nvme0n1.read(qpair, buf, i).waitdone()
        assert buf[8] == 0x55
        assert buf[0] == i

    nvme0n1.read(qpair, buf, 32*8).waitdone()
    assert buf[8] == 0
    assert buf[0] == 0


def test_buffer_access_overflow():
    b = d.Buffer(1000)

    b[999] = 0
    assert b[999] == 0

    with pytest.raises(IndexError):
        b[1000] = 0

    with pytest.raises(IndexError):
        assert b[1000] == 0


@pytest.mark.parametrize("offset", [0, 4, 16, 32, 512, 800, 1024, 3000])
def test_page_offset(nvme0, nvme0n1, qpair, buf, offset):
    # fill the data
    write_buf = d.Buffer(512)
    nvme0n1.write(qpair, write_buf, 0x5aa5).waitdone()

    # read the data to different offset and check lba
    buf.offset = offset
    nvme0n1.read(qpair, buf, 0x5aa5).waitdone()
    assert buf[offset] == 0xa5
    assert buf[offset+1] == 0x5a


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


def test_buffer_dump_large():
    b = d.Buffer(5000)
    b.dump()

    b = d.Buffer(6*1024, pvalue=100, ptype=0xbeef)
    assert type(b.dump(1)) == str

    b = d.Buffer(256*1024, "pattern buffer", pvalue=101, ptype=32)
    logging.info(b.dump(64))


@pytest.mark.parametrize("repeat", range(2))
def test_create_many_qpair(nvme0, repeat):
    ql = []
    for i in range(16):
        ql.append(d.Qpair(nvme0, 8))
    for q in ql:
        q.delete()

    for i in range(50):
        q = d.Qpair(nvme0, 80)
        q.delete()


def test_set_get_features(nvme0):
    nvme0.setfeatures(0x7, cdw11=(15<<16)+15)
    nvme0.setfeatures(0x7, cdw11=(15<<16)+15)
    nvme0.waitdone(2)
    nvme0.getfeatures(0x7)
    nvme0.waitdone()
    assert (15<<16)+15 == nvme0.getfeatures(0x7).waitdone()


def test_pcie_reset(nvme0, pcie, nvme0n1):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        ret = buf.data(115, 112)
        logging.info("power cycles: %d" % ret)
        return ret

    nvme0n1.ioworker(io_size=2, time=2).start().close()
    powercycle = get_power_cycles(nvme0)
    pcie.reset()
    nvme0.reset()
    assert powercycle == get_power_cycles(nvme0)
    nvme0n1.ioworker(io_size=2, time=2).start().close()

    
def test_pcie_reset_user_fn(nvme0, pcie, nvme0n1):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        ret = buf.data(115, 112)
        logging.info("power cycles: %d" % ret)
        return ret

    def print_fn():
        logging.info("here")
        
    nvme0n1.ioworker(io_size=2, time=2).start().close()
    powercycle = get_power_cycles(nvme0)
    pcie.reset(print_fn)
    nvme0.reset()
    assert powercycle == get_power_cycles(nvme0)
    nvme0n1.ioworker(io_size=2, time=2).start().close()

    
def _test_pcie_flr_reset(nvme0, pcie, nvme0n1):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        ret = buf.data(115, 112)
        logging.info("power cycles: %d" % ret)
        return ret

    nvme0n1.ioworker(io_size=2, time=2).start().close()
    powercycle = get_power_cycles(nvme0)
    pcie.flr()
    nvme0.reset()
    assert powercycle == get_power_cycles(nvme0)
    nvme0n1.ioworker(io_size=2, time=2).start().close()


@pytest.mark.parametrize("control", [0, 1, 2, 3, 0])
def test_pcie_aspm(pcie, nvme0n1, control):
    logging.info("current ASPM: %d" % pcie.aspm)
    nvme0n1.ioworker(io_size=2, time=2).start().close()
    pcie.aspm = control
    logging.info("current ASPM: %d" % pcie.aspm)
    nvme0n1.ioworker(io_size=2, time=2).start().close()


def test_pcie_aspm_l1_and_d3hot(pcie, nvme0n1):
    assert pcie.aspm == 0
    pcie.aspm = 2
    pcie.power_state = 3
    time.sleep(1)
    pcie.power_state = 0
    pcie.aspm = 0
    nvme0n1.ioworker(io_size=2, time=2).start().close()

    pcie.power_state = 3
    pcie.aspm = 2
    time.sleep(1)
    pcie.aspm = 0
    pcie.power_state = 0
    nvme0n1.ioworker(io_size=2, time=2).start().close()
    assert pcie.aspm == 0


def test_pcie_aspm_off_and_d3hot(pcie, nvme0n1):
    assert pcie.aspm == 0
    pcie.power_state = 3
    time.sleep(1)
    pcie.power_state = 0
    assert pcie.aspm == 0
    nvme0n1.ioworker(io_size=2, time=2).start().close()


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


def test_write_fua_latency(nvme0n1, nvme0, qpair, buf):
    now = time.time()
    for i in range(100):
        nvme0n1.write(qpair, buf, 0, 8).waitdone()
    non_fua_time = time.time()-now
    logging.info("normal write latency %fs" % non_fua_time)

    now = time.time()
    for i in range(100):
        # write with FUA enabled
        nvme0n1.write(qpair, buf, 0, 8, 1<<14).waitdone()
    fua_time = time.time()-now
    logging.info("FUA write latency %fs" % fua_time)
    assert non_fua_time < fua_time
    

def test_write_limited_retry(nvme0n1, nvme0, qpair, buf):
    nvme0n1.write(qpair, buf, 0, 8, 1<<31).waitdone()


def test_write_huge_data(nvme0n1, qpair):
    buf = d.Buffer(2*1024*1024)

    with pytest.warns(UserWarning, match="ERROR status: 00/02"):
        nvme0n1.write(qpair, buf, 0, 1*1024*1024//512).waitdone()

    with pytest.warns(UserWarning, match="ERROR status: 00/02"):
        with pytest.raises(AssertionError):
            nvme0n1.write(qpair, buf, 0, 2*1024*1024//512).waitdone()


def test_read_limited_retry(nvme0n1, nvme0):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)
    nvme0n1.read(q, buf, 0, 8, 1<<31).waitdone()
    q.delete()


def test_subsystem_reset(nvme0, subsystem, nvme0n1):
    logging.info("CAP: 0x%x, NSSRS: %d" % (nvme0.cap, (nvme0.cap>>36)&0x1))

    def get_power_cycles(nvme1):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        logging.info("power cycles: %d" % buf.data(115, 112))
        return buf.data(115, 112)

    powercycle = get_power_cycles(nvme0)
    subsystem.reset()
    nvme0.reset()
    assert powercycle == get_power_cycles(nvme0)

    nvme0n1.ioworker(io_size=2, time=2).start().close()


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
    for q in ql:
        q.delete()


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
    time.sleep(1)
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

    q.delete()
    q2.delete()


def test_io_qpair_msix_interrupt_coalescing(nvme0, nvme0n1):
    buf = d.Buffer(4096)
    q = d.Qpair(nvme0, 8)
    q.msix_clear()
    assert not q.msix_isset()

    # aggregation time: 100*100us=0.01s, aggregation threshold: 2
    nvme0.setfeatures(8, cdw11=(200<<8)+10)

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
    q.delete()


def test_ioworker_fast_complete(nvme0n1):
    nvme0n1.ioworker(io_size=64, lba_align=64,
                     lba_random=False, qdepth=128,
                     region_end=512, io_count=100,
                     read_percentage=0).start().close()

    io_per_second = []
    nvme0n1.ioworker(io_size=64, lba_align=64,
                     lba_random=False,
                     region_end=512, io_count=100,
                     iops=10, qdepth=8,
                     read_percentage=0,
                     output_io_per_second=io_per_second).start().close()
    assert len(io_per_second) == 10


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
    nvme0.reset()
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
    nvme0.reset()
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
    nvme0.reset()
    init_time_write_clean = time.time()-start_time
    assert get_power_cycles(nvme0) == powercycle+1

    # dirty init time should be longer than clean init time
    logging.info("clean init time %f, dirty init time %f" %
                 (init_time_write_clean, init_time_write))


@pytest.mark.parametrize("repeat", range(20))
def test_subsystem_power_cycle(nvme0, subsystem, repeat):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        logging.info("power cycles: %d" % buf.data(115, 112))
        return buf.data(115, 112)

    import time
    start_time = time.time()
    powercycle = get_power_cycles(nvme0)

    subsystem.power_cycle(10)
    nvme0.reset()
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
    nvme0.reset()
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
    nvme0.reset()
    assert powercycle+1 == get_power_cycles(nvme0)


def test_controller_reset(nvme0, nvme0n1):
    def get_power_cycles(nvme0):
        buf = d.Buffer(512)
        nvme0.getlogpage(2, buf, 512).waitdone()
        logging.info("power cycles: %d" % buf.data(115, 112))
        return buf.data(115, 112)

    powercycle = get_power_cycles(nvme0)
    logging.info("power cycles: %d" % powercycle)
    nvme0.reset()
    assert get_power_cycles(nvme0) == powercycle
    nvme0n1.ioworker(io_size=2, time=2).start().close()


def test_get_smart_data(nvme0):
    smart_buffer = d.Buffer(4096, "smart data buffer")
    nvme0.getlogpage(0x2, smart_buffer, 512)
    nvme0.waitdone()
    assert smart_buffer[2] == 0 or smart_buffer[2] == 1


def test_aer_cb_mixed_with_admin_commands(nvme0, buf):
    def aer_cb(cpl):
        logging.info("0x%x" % cpl[3])
    # this is the 2nd aer, 1st is in default nvme init
    nvme0.aer(cb=aer_cb)

    for i in range(50):
        nvme0.getfeatures(7).waitdone()

    for i in range(50):
        nvme0.getlogpage(0x81, buf, 20).waitdone()

    # ABORTED - BY REQUEST (00/07)
    with pytest.warns(UserWarning, match="ERROR status: 00/07"):
        for i in range(100):
            nvme0.abort(127-i).waitdone()

    # no more aer: in pytest way
    with pytest.raises(TimeoutError):
        nvme0.waitdone()

    # no more aer: in generic python 
    try:
        nvme0.waitdone()
    except TimeoutError as e:
        assert str(e) == "pynvme timeout in driver"


def test_aer_mixed_with_admin_commands(nvme0, buf):
    for i in range(5000):
        nvme0.getfeatures(7).waitdone()

    for i in range(5000):
        nvme0.getlogpage(0x81, buf, 20).waitdone()

    # aer will not complete, timeout in driver
    with pytest.raises(TimeoutError):
        nvme0.waitdone()

    # ABORTED - BY REQUEST (00/07)
    with pytest.warns(UserWarning, match="ERROR status: 00/07"):
        for i in range(100):
            nvme0.abort(127-i).waitdone()

    # no more aer
    with pytest.raises(TimeoutError):
        nvme0.waitdone()


def test_abort_aer_commands(nvme0):
    aerl = nvme0.id_data(259)+1

    # another one is sent in defaul nvme init
    logging.info(aerl)
    for i in range(aerl-1):
        nvme0.aer()

    # ASYNC LIMIT EXCEEDED (01/05)
    with pytest.warns(UserWarning, match="ERROR status: 01/05"):
        nvme0.aer()
        nvme0.getfeatures(7).waitdone()

    # no timeout happen on aer
    time.sleep(15)

    # ABORTED - BY REQUEST (00/07)
    with pytest.warns(UserWarning, match="ERROR status: 00/07"):
        for i in range(100):
            nvme0.abort(127-i).waitdone()


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


def test_ioworker_cmdlog_list(nvme0n1):
    cmdlog_list = [None]*11
    nvme0n1.ioworker(io_size=1, time=1,
                     output_cmdlog_list=cmdlog_list,
                     iops=10, qdepth=2, lba_random=False).start().close()

    # check cmdlog
    for i, cmd in enumerate(cmdlog_list[1:]):
        assert cmd[0] == i
        assert cmd[1] == 1
        assert cmd[2] == 2
    assert cmdlog_list[0][0] == 0
    assert cmdlog_list[0][1] == 0
    assert cmdlog_list[0][2] == 0


@pytest.mark.parametrize("lba_random", [True, False, 100, 70, 51, 10, 2, 0])
def test_ioworker_lba_random_percentage(nvme0n1, lba_random):
    cmdlog_list = [None]*100
    nvme0n1.ioworker(io_size=8, lba_random=lba_random,
                     output_cmdlog_list = cmdlog_list,
                     io_count=100).start().close()


def test_ioworker_lba_random_illegal(nvme0n1):
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=8, lba_random=101, time=1).start().close()
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=8, lba_random=[0, 1], time=1).start().close()


def test_ioworker_lba_step_multiple(nvme0n1):
    cmdlog_lists = [[None]*10, [None]*10, [None]*10, [None]*10]
    with nvme0n1.ioworker(io_size=1, io_count=10, lba_start=0,
                          lba_align=1, lba_step=4,
                          output_cmdlog_list=cmdlog_lists[0],
                          qdepth=2, lba_random=False), \
         nvme0n1.ioworker(io_size=1, io_count=10, lba_start=1,
                          lba_align=1, lba_step=4,
                          output_cmdlog_list=cmdlog_lists[1],
                          qdepth=2, lba_random=False), \
         nvme0n1.ioworker(io_size=1, io_count=10, lba_start=2,
                          lba_align=1, lba_step=4,
                          output_cmdlog_list=cmdlog_lists[2],
                          qdepth=2, lba_random=False), \
         nvme0n1.ioworker(io_size=1, io_count=10, lba_start=3,
                          lba_align=1, lba_step=4,
                          output_cmdlog_list=cmdlog_lists[3],
                          qdepth=2, lba_random=False):

        pass

    logging.info(cmdlog_lists)
    assert cmdlog_lists[0][0][0] == 0
    assert cmdlog_lists[0][9][0] == 36
    assert cmdlog_lists[1][0][0] == 1
    assert cmdlog_lists[1][9][0] == 37
    assert cmdlog_lists[2][0][0] == 2
    assert cmdlog_lists[2][9][0] == 38
    assert cmdlog_lists[3][0][0] == 3
    assert cmdlog_lists[3][9][0] == 39


def test_ioworker_lba_step(nvme0n1):
    cmdlog_list = [None]*10
    nvme0n1.ioworker(io_size=1, io_count=10, lba_step=2,
                     output_cmdlog_list=cmdlog_list,
                     qdepth=2, lba_random=False).start().close()
    assert cmdlog_list[9][0] == 18

    cmdlog_list = [None]*10
    nvme0n1.ioworker(io_size=1, io_count=10, lba_step=5,
                     output_cmdlog_list=cmdlog_list,
                     qdepth=2, lba_random=False).start().close()
    assert cmdlog_list[9][0] == 45

    cmdlog_list = [None]*10
    nvme0n1.ioworker(io_size=1, io_count=10, lba_step=1,
                     output_cmdlog_list=cmdlog_list,
                     qdepth=2, lba_random=False).start().close()
    assert cmdlog_list[9][0] == 9

    cmdlog_list = [None]*10
    nvme0n1.ioworker(io_size=3, io_count=20, lba_step=1, lba_align=1,
                     output_cmdlog_list=cmdlog_list,
                     qdepth=2, lba_random=False).start().close()
    assert cmdlog_list[0][0] == 10
    assert cmdlog_list[9][0] == 19

    cmdlog_list = [None]*10
    nvme0n1.ioworker(io_size=8, io_count=20, lba_step=0, lba_align=1,
                     output_cmdlog_list=cmdlog_list, lba_start=10,
                     qdepth=2, lba_random=False).start().close()
    assert cmdlog_list[0][0] == 10
    assert cmdlog_list[9][0] == 10

    cmdlog_list = [None]*10
    nvme0n1.ioworker(io_size=1, io_count=10, lba_step=-1, lba_align=1,
                     output_cmdlog_list=cmdlog_list, lba_start=100,
                     qdepth=2, lba_random=False).start().close()
    assert cmdlog_list[0][0] == 100
    assert cmdlog_list[9][0] == 91

    cmdlog_list = [None]*10
    nvme0n1.ioworker(io_size=8, io_count=20, lba_step=-4, lba_align=1,
                     output_cmdlog_list=cmdlog_list, lba_start=100,
                     qdepth=2, lba_random=False).start().close()
    assert cmdlog_list[0][0] == 60
    assert cmdlog_list[9][0] == 24
    assert cmdlog_list[9][1] == 8


def test_ioworker_random_seed(nvme0n1):
    cmdlog_list = [None]*11

    # base
    nvme0n1.ioworker(io_size=1, time=1,
                     output_cmdlog_list=cmdlog_list,
                     iops=10, qdepth=2).start().close()
    lba_compare = cmdlog_list[9][0]

    # same ioworker
    nvme0n1.ioworker(io_size=1, time=1,
                     output_cmdlog_list=cmdlog_list,
                     iops=10, qdepth=2).start().close()
    assert lba_compare != cmdlog_list[9][0]

    # write v.s. read
    nvme0n1.ioworker(io_size=1, time=1,
                     output_cmdlog_list=cmdlog_list,
                     read_percentage=0,
                     iops=10, qdepth=2).start().close()
    assert lba_compare != cmdlog_list[9][0]

    nvme0n1.ioworker(io_size=1, time=1,
                     output_cmdlog_list=cmdlog_list,
                     read_percentage=0,
                     iops=10, qdepth=2).start().close()
    assert lba_compare != cmdlog_list[9][0]


def test_ioworker_simplified(nvme0n1):
    nvme0n1.ioworker(io_size=2, time=2).start().close()


def test_ioworker_op_dict(nvme0n1):
    op_percentage = {2: 100}
    nvme0n1.ioworker(io_size=2, time=2, op_percentage=op_percentage).start().close()
    test1 = op_percentage[2]

    op_percentage = {2: 100, 1:0}
    nvme0n1.ioworker(io_size=2, time=2, op_percentage=op_percentage).start().close()
    assert abs(op_percentage[2]-test1)/test1 < 0.1
    assert op_percentage[1] == 0

    op_percentage = {2: 50, 1:50}
    nvme0n1.ioworker(io_size=2, time=2, op_percentage=op_percentage).start().close()
    assert abs(op_percentage[1]-op_percentage[2])/op_percentage[1] < 0.1


def test_ioworker_op_dict_invalid(nvme0n1):
    with pytest.raises(AssertionError):
        op_percentage = {2: 50, 1:49}
        nvme0n1.ioworker(io_size=2, time=2, op_percentage=op_percentage).start().close()

    with pytest.raises(AssertionError):
        op_percentage = {2: 50, 1:61}
        nvme0n1.ioworker(io_size=2, time=2, op_percentage=op_percentage).start().close()


def test_ioworker_op_dict_trim(nvme0n1):
    nvme0n1.ioworker(io_size=2, lba_random=30, time=2, op_percentage={2: 40, 9: 30, 1: 30}).start().close()

    op_percentage = {2: 40, 9: 60}
    ret = nvme0n1.ioworker(io_size=2, time=2, op_percentage=op_percentage).start().close()
    assert ret.io_count_write == 0

    opcode_counter = {2: 40, 9: 30, 1: 30}
    ret = nvme0n1.ioworker(io_size=2, time=2, op_percentage=opcode_counter).start().close()
    assert ret.io_count_read == opcode_counter[2]
    assert ret.io_count_nonread == opcode_counter[9]+opcode_counter[1]
    logging.info(ret)
    logging.info(opcode_counter)
    assert ret.io_count_write == opcode_counter[1]


def test_ioworker_op_dict_flush(nvme0n1):
    opcode_counter = {2: 30, 9: 30, 1: 30, 0: 10}
    ret = nvme0n1.ioworker(io_size=2, time=2, op_percentage=opcode_counter).start().close()
    logging.info(ret)
    logging.info(opcode_counter)
    assert ret.io_count_read == opcode_counter[2]
    assert opcode_counter[1]//opcode_counter[0] >= 2


def test_ioworker_iosize_inputs(nvme0n1):
    d.srand(0x58e7f337)
    nvme0n1.ioworker(io_size=16, time=10).start().close()
    nvme0n1.ioworker(io_size=[1, 8], time=1).start().close()
    nvme0n1.ioworker(io_size=range(1, 8), time=1).start().close()
    nvme0n1.ioworker(io_size={1: 2, 8: 8}, time=1).start().close()
    nvme0n1.ioworker(io_size={1: 2, 8: 8}, lba_align=[1, 8], time=1).start().close()


@pytest.mark.parametrize("repeat", range(2))
def test_ioworker_jedec_workload(nvme0n1, repeat):
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
                     distribution = distribution,
                     read_percentage=0,
                     ptype=0xbeef, pvalue=100,
                     time=1).start().close()


@pytest.mark.parametrize("repeat", [1, 10, 100, 1000])
def test_ioworker_io_sequence(nvme0n1, repeat):
    # (time, op, slba, nlba)
    nvme0n1.ioworker(io_sequence=[(0, 2, 0, 1)]*repeat).start().close()


@pytest.mark.parametrize("repeat", [1, 10, 100, 1000])
def test_iowoker_io_sequence_5s(nvme0n1, repeat):
    start = time.time()
    nvme0n1.ioworker(io_sequence=[(5000001, 2, 0, 1)]*repeat).start().close()
    assert time.time()-start > 5


def test_ioworker_io_sequence_big_xfer(nvme0n1):
    nvme0n1.ioworker(io_sequence=[(0, 2, 0, 256)]).start().close()


def test_ioworker_io_sequence_read_write_trim_flush_uncorr(nvme0n1):
    cmd_seq = [(000000, 1, 0, 8),
               (200000, 2, 3, 1),
               (400000, 1, 2, 1),
               (600000, 9, 1, 1),
               (800000, 4, 0, 8),
               (1000000, 0, 0, 0)]
    cmdlog_list = [None]*len(cmd_seq)

    r = nvme0n1.ioworker(io_sequence=cmd_seq,
                         output_cmdlog_list=cmdlog_list).start().close()

    assert r.mseconds > 1000
    assert cmdlog_list[-1][2] == 0
    assert cmdlog_list[-2][2] == 4
    assert cmdlog_list[-3][2] == 9
    assert cmdlog_list[-4][2] == 1
    assert cmdlog_list[-5][2] == 2
    assert cmdlog_list[-6][2] == 1


def test_ioworker_io_sequence_uncorr_and_read(nvme0n1):
    cmd_seq = [(000000, 1, 0, 8),
               (200000, 4, 0, 8),
               (400000, 2, 3, 1)]
    cmdlog_list = [None]*len(cmd_seq)

    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        nvme0n1.ioworker(io_sequence=cmd_seq,
                         output_cmdlog_list=cmdlog_list).start().close()

    nvme0n1.format(512)


@pytest.mark.parametrize("repeat", range(2))
def test_ioworker_distribution(nvme0n1, repeat):
    distribution = [0]*100
    distribution[1] = 10000
    nvme0n1.ioworker(io_size=8, lba_align=8,
                     lba_random=True, qdepth=16,
                     distribution = distribution,
                     read_percentage=0, time=1).start().close()

    distribution = [100]*100
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=True, qdepth=64,
                         distribution = distribution,
                         read_percentage=100, time=1).start().close()
    logging.debug(r)

    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=True, qdepth=64,
                         read_percentage=100, time=1).start().close()
    logging.debug(r)


def test_ioworker_simplified_context(nvme0n1):
    with nvme0n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=2) as w:
        logging.info("ioworker context start")
    logging.info("ioworker context finish")


def test_ioworker_output_io_per_latency(nvme0n1, nvme0):
    nvme0n1.format(512)

    output_percentile_latency = dict.fromkeys([10, 50, 90, 99, 99.9, 99.99, 99.999, 99.99999])
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=False, qdepth=32,
                         read_percentage=100, time=10,
                         output_percentile_latency=output_percentile_latency).start().close()
    logging.debug(output_percentile_latency)
    heavy_latency_average = r.latency_average_us
    max_iops = (r.io_count_read+r.io_count_nonread)*1000//r.mseconds
    assert len(r.latency_distribution) == 1000000

    # limit iops, should get smaller latency
    output_percentile_latency = dict.fromkeys([10, 50, 90, 99, 99.9, 99.99, 99.999, 99.99999])
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=False, qdepth=32,
                         iops=max_iops//2,
                         read_percentage=100, time=10,
                         output_percentile_latency=output_percentile_latency).start().close()
    logging.debug(output_percentile_latency)
    assert r.latency_average_us < heavy_latency_average

    output_io_per_second = []
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=False, qdepth=32,
                         read_percentage=0, time=10,
                         output_io_per_second=output_io_per_second,
                         output_percentile_latency=output_percentile_latency).start().close()
    assert len(output_io_per_second) == 10
    logging.debug(output_percentile_latency)
    assert output_percentile_latency[99.999] <= output_percentile_latency[99.99999]


def test_ioworker_iops_deep_queue(nvme0n1):
    r = nvme0n1.ioworker(io_size=8,
                         lba_random=True,
                         qdepth=1024,
                         read_percentage=100,
                         iops=2000,
                         time=1).start().close()
    assert r.io_count_read <= 1024+2000
    r = nvme0n1.ioworker(io_size=8,
                         lba_random=True,
                         qdepth=1024,
                         read_percentage=100,
                         iops=2000,
                         time=2).start().close()
    assert r.io_count_read <= 1024+2*2000


def test_ioworker_output_io_per_second(nvme0n1, nvme0):
    nvme0n1.format(512)

    output_io_per_second = []
    nvme0n1.ioworker(io_size=8, lba_align=16,
                     lba_random=True, qdepth=8,
                     read_percentage=0, time=7,
                     iops=10,
                     output_io_per_second=output_io_per_second).start().close()
    logging.debug(output_io_per_second)
    assert len(output_io_per_second) == 7
    assert output_io_per_second[0] != 0
    assert output_io_per_second[-1] == 10

    output_io_per_second = []
    r = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=True, qdepth=16,
                         read_percentage=100, time=10,
                         iops=12345,
                         output_io_per_second=output_io_per_second).start().close()
    logging.debug(output_io_per_second)
    logging.debug(r)
    assert len(output_io_per_second) == 10
    assert output_io_per_second[0] != 0
    assert output_io_per_second[-1] >= 12344
    assert output_io_per_second[-1] <= 12346
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


@pytest.mark.parametrize("depth", [256, 512, 1024])
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
    nvme0n1.ioworker(io_size=256, lba_align=64,
                     lba_random=False, qdepth=1024,
                     read_percentage=100, time=2).start().close()


def test_ioworker_memory_fail(nvme0n1):
    ioworkers = []
    for i in range(16):
        w = nvme0n1.ioworker(io_size=256,
                             lba_random=False,
                             qdepth=1024,
                             read_percentage=100,
                             time=10).start()
        ioworkers.append(w)

    with pytest.warns(UserWarning, match="ioworker host ERROR -5: buffer pool alloc fail"):
        for w in ioworkers:
            w.close()


@pytest.mark.parametrize("qcount", [1, 2, 4, 8, 16])
def test_ioworker_iops_multiple_queue(nvme0, qcount):
    region_end=256*1024*8 # 1GB space
    nvme0n1 = d.Namespace(nvme0, 1, region_end)

    l = []
    io_total = 0
    for i in range(qcount):
        a = nvme0n1.ioworker(io_size=8,
                             region_end=region_end,
                             lba_random=False,
                             read_percentage=100,
                             time=10).start()
        l.append(a)

    for a in l:
        r = a.close()
        logging.info(r)
        io_total += (r.io_count_read+r.io_count_nonread)

    logging.info("Q %d IOPS: %.3fK" % (qcount, io_total/10000))
    nvme0n1.close()


@pytest.mark.parametrize("qcount", [1, 2, 4, 8, 16])
def test_ioworker_bandwidth_multiple_queue(nvme0, qcount):
    region_end=256*1024*8 # 1GB space
    nvme0n1 = d.Namespace(nvme0, 1, region_end)

    l = []
    io_total = 0
    io_size = 128
    for i in range(qcount):
        a = nvme0n1.ioworker(io_size=io_size,
                             region_start=0,
                             region_end=region_end,
                             lba_random=False,
                             qdepth=64,
                             read_percentage=100,
                             time=10).start()
        l.append(a)

    for a in l:
        r = a.close()
        logging.debug(r)
        io_total += (r.io_count_read+r.io_count_nonread)

    logging.info("Q %d: %dMB/s" % (qcount, (io_size*512*io_total/1000)/10000))
    nvme0n1.close()


@pytest.mark.parametrize("qcount", [1, 1, 1, 1])
def test_ioworker_iops_multiple_queue_fob(nvme0, qcount):
    nvme0n1 = d.Namespace(nvme0)
    nvme0n1.format(512)
    nvme0n1.close()
    test_ioworker_iops_multiple_queue(nvme0, qcount)


@pytest.mark.parametrize("repeat", range(2))
def test_namespace_init_after_reset(nvme0, nvme0n1, repeat):
    nvme0.reset()


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
                         lba_random=False, qdepth=1025,
                         read_percentage=100, time=2).start().close()

    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=8, lba_align=64,
                         lba_random=False, qdepth=5000,
                         read_percentage=100, time=2).start().close()


def test_ioworker_invalid_io_size(nvme0, nvme0n1):
    # format to clear all data before test
    nvme0n1.format(512)

    assert nvme0.mdts//512 == 256
    nvme0n1.ioworker(io_size=nvme0.mdts//512, lba_align=64,
                     lba_random=False, qdepth=4,
                     read_percentage=100, time=2).start().close()

    with pytest.warns(UserWarning, match="ioworker host ERROR"):
        nvme0n1.ioworker(io_size=nvme0.mdts//512+1, lba_align=64,
                         lba_random=False, qdepth=4,
                         read_percentage=100, time=2).start().close()

    with pytest.warns(UserWarning, match="ioworker host ERROR -1"):
        nvme0n1.ioworker(io_size=0x10000, lba_align=64,
                         lba_random=False, qdepth=4,
                         read_percentage=100, time=2).start().close()


def test_ioworker_iops_confliction_after_reset(nvme0, pcie):
    pcie.reset()
    nvme0.reset()

    # create namespace with limited verify scope
    nvme0n1 = d.Namespace(nvme0, 1, 1000*1000//4)
    assert True == nvme0n1.verify_enable()
    nvme0n1.format(512)

    start_time = time.time()
    ww = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=0, time=10,
                          qprio=0, qdepth=16).start()
    wr = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                          lba_random=False,
                          region_start=0, region_end=1000,
                          read_percentage=100, time=10,
                          qprio=0, qdepth=16).start()

    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        wr.close()

    report = ww.close()
    assert report.error == 0
    assert time.time()-start_time > 2.0
    nvme0n1.close()


def test_ioworker_iops(nvme0n1):
    import time
    start_time = time.time()
    w = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=100,
                         iops=1000, io_count=10000, time=1000*3600,
                         qprio=0, qdepth=16)
    w.start()
    report = w.close()
    assert report['io_count_read'] == 10000
    assert report['io_count_nonread'] == 0
    assert report.io_count_write == 0
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
    assert time.time()-start_time > 9
    assert time.time()-start_time < 20


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
    assert time.time()-start_time > 9
    assert time.time()-start_time < 20

    w = nvme0n1.ioworker(io_size=8, io_count=1, qdepth=64).start().close()
    assert w.io_count_read == 1
    assert w.io_count_nonread == 0

    
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
    assert time.time()-start_time > 9
    assert time.time()-start_time < 20


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
    assert time.time()-start_time > 9
    assert time.time()-start_time < 20


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
    assert time.time()-start_time > 9
    assert time.time()-start_time < 20


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
    qpair.delete()


@pytest.mark.parametrize("repeat", range(2))
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


def test_io_conflict(nvme0, nvme0n1, buf, verify):
    assert verify

    qpair = d.Qpair(nvme0, 1024)

    # send write and read command
    for i in range(1000):
        nvme0n1.write(qpair, buf, 0)
    qpair.waitdone(1000)
    qpair.delete()


def test_ioworker_trim_rw_without_confliction(nvme0n1, verify):
    assert verify

    nvme0n1.format(512)

    r = nvme0n1.ioworker(io_size=256,
                         lba_align=512,
                         lba_random=True,
                         region_end=0x1000,
                         qdepth=64, 
                         time=100,
                         op_percentage={2: 40, 1: 20, 8: 20, 9: 20}).start().close()
    logging.info(r)


@pytest.mark.parametrize("repeat", range(2))
def test_ioworker_rw_mix_without_confliction(nvme0n1, verify, repeat):
    assert verify

    nvme0n1.format(512)

    # no confliction of mixed rw in the single ioworker with LBA lock
    r = nvme0n1.ioworker(io_size=8,
                         lba_random=True,
                         region_end=1000,
                         read_percentage=50,
                         time=30).start().close()
    logging.info(r)


def test_ioworker_read_and_write_confliction(nvme0n1, nvme0, verify):
    # """read write confliction will cause data mismatch.
    #
    # When the same LBA the read and write commands are operating on, NVMe
    # spec does not garentee the order of read and write operation, so the
    # data of read command got could be old data or the new data of the write
    # command just written.
    # """

    assert verify

    nvme0n1.format(512)

    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        with nvme0n1.ioworker(io_size=8,
                              lba_random=0,
                              region_end=8,
                              read_percentage=0,
                              time=10), \
             nvme0n1.ioworker(io_size=8,
                              lba_random=50,
                              region_end=8,
                              read_percentage=100,
                              time=10):
            pass


def test_ioworker_distribution_read_write_confliction(nvme0n1, verify):
    assert verify

    distribution = [0]*100
    distribution[1] = 10000
    with nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=True, qdepth=64,
                          distribution = distribution,
                          read_percentage=0, time=10), \
         nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=True, qdepth=64,
                          distribution = distribution,
                          read_percentage=100, time=10):
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
    # One solution is to separate read and write to differnt IOWorkers
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
    assert r.io_count_nonread == 1
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
    q.delete()


def test_cmd_cb_features(nvme0):
    orig_config = 0

    # every callback function has to have different names
    def getfeatures_cb_1(cdw0, status):
        nonlocal orig_config; orig_config = cdw0
    nvme0.getfeatures(5, cb=getfeatures_cb_1).waitdone()

    def setfeatures_cb_1(cdw0, status):
        pass
    nvme0.setfeatures(5, cdw11=orig_config+1, cb=setfeatures_cb_1).waitdone()

    # nesting callbacks: only submit commands in callback, but waitdone() outside of callbacks
    def getfeatures_cb_2(cdw0, status):
        assert cdw0 == orig_config+1
        # cannot call waitdone in callback functions
        nvme0.setfeatures(5, cdw11=orig_config)
    # call waitdone one more time for setfeatures in above callback
    nvme0.getfeatures(5, cb=getfeatures_cb_2).waitdone(2)

    def getfeatures_cb_3(cdw0, status):
        assert cdw0 == orig_config
    nvme0.getfeatures(5, cb=getfeatures_cb_3).waitdone()


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
    io_qpair.delete()


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
    io_qpair.delete()


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
    io_qpair.delete()


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
    io_qpair.delete()


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
    io_qpair.delete()


def test_ioworker_timeout_command(nvme0, nvme0n1):
    now = time.time()
    r = nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=2, io_count=1000, time=5,
                         qprio=0, qdepth=2).start().close()
    assert time.time()-now > 5
    assert time.time()-now < 10


def test_reentry_waitdone_io_qpair(nvme0, nvme0n1):
    b = d.Buffer()
    q = d.Qpair(nvme0, 10)

    nvme0n1.write(q, b, 0, 8).waitdone()

    def read_cb_2(cdw0, status):
        nvme0n1.read(q, b, 3, 1)
    nvme0n1.read(q, b, 4, 1, cb=read_cb_2).waitdone(2)

    def read_cb(cdw0, status):
        nvme0n1.read(q, b, 1, 1).waitdone()
    with pytest.warns(UserWarning, match="ASSERT: cannot re-entry waitdone()"):
        nvme0n1.read(q, b, 2, 1, cb=read_cb).waitdone()
    q.delete()


def test_ioworker_end(nvme0n1):
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
        nvme0n1.send_cmd(0, q, nsid=0).waitdone()

    # flush command
    nvme0n1.send_cmd(0x0, q, nsid=1).waitdone()
    q.delete()


def test_ioworker_vscode_showcase(nvme0n1, qpair):
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
                          qdepth=8, read_percentage=0,
                          iops=10, time=10):
         pass


def test_ioworker_invalid_read_percentage(nvme0n1):
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=128, lba_random=False,
                         read_percentage=1000, time=1).start().close()
    with pytest.raises(AssertionError):
        nvme0n1.ioworker(io_size=128, lba_random=False,
                         read_percentage=101, time=1).start().close()


def test_ioworker_cpu_usage(nvme0n1):
    r = nvme0n1.ioworker(io_size=128, lba_random=False,
                         read_percentage=100, time=1).start().close()
    logging.info(r)
    large_io_cpu = r.cpu_usage

    r = nvme0n1.ioworker(io_size=8, lba_random=True,
                         read_percentage=100, time=1).start().close()
    logging.info(r)
    small_io_cpu = r.cpu_usage

    assert large_io_cpu < small_io_cpu


def test_ioworker_average_latency(nvme0n1):
    r1 = nvme0n1.ioworker(io_size=128, lba_random=False,
                         read_percentage=0, time=1).start().close()
    r2 = nvme0n1.ioworker(io_size=8, lba_random=True,
                         read_percentage=100, time=1).start().close()
    assert r1.latency_average_us > r2.latency_average_us


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

    q.delete()


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
    #with pytest.warns(UserWarning, match="ERROR status: 00/0a"):
    nvme0n1.send_cmd(1|(1<<8), q, b, 1, 8, 0, 0).waitdone()
    #with pytest.warns(UserWarning, match="ERROR status: 00/0a"):
    nvme0n1.send_cmd(5|(1<<9), q, b, 1, 8, 0, 0).waitdone()

    q.delete()


def test_raw_write_read(nvme0, nvme0n1, qpair, verify):
    buf = d.Buffer(512, ptype=32, pvalue=0x5aa5a55a)

    # use generic cmd to write without pynvme's injected data
    nvme0n1.send_cmd(1, qpair, buf).waitdone()  # write LBA 0

    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        nvme0n1.send_cmd(2, qpair, buf).waitdone()  # write LBA 0
    assert buf[0] == 0x5a
    assert buf[1] == 0xa5

    with pytest.warns(UserWarning, match="ERROR status: 02/81"):
        nvme0n1.read(qpair, buf, 0).waitdone()
    assert buf[0] == 0x5a
    assert buf[1] == 0xa5

    buf = d.Buffer(512, ptype=32, pvalue=0)
    nvme0n1.send_cmd(1, qpair, buf).waitdone()  # write LBA 0
    nvme0n1.read(qpair, buf, 0).waitdone()
    assert buf[0] == 0
    assert buf[1] == 0


def test_raw_write_read_without_verify(nvme0, nvme0n1, qpair):
    buf = d.Buffer(512, ptype=32, pvalue=0x5aa5a55a)
    nvme0n1.send_cmd(1, qpair, buf).waitdone()  # write LBA 0

    nvme0n1.send_cmd(2, qpair, buf).waitdone()  # write LBA 0
    assert buf[0] == 0x5a
    assert buf[1] == 0xa5

    nvme0n1.read(qpair, buf, 0).waitdone()
    assert buf[0] == 0x5a
    assert buf[1] == 0xa5


@pytest.mark.parametrize("lba_size", [512])
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
    q.delete()


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
    q.delete()


def test_ioworker_stress(nvme0n1):
    for i in range(1000):
        logging.info(i)
        with nvme0n1.ioworker(io_size=8, lba_align=8,
                              lba_random=False, io_count=1,
                              qdepth=16, read_percentage=100):
            pass


def test_ioworker_stress_multiple_small_too_many(nvme0n1):
    l = []
    for i in range(17):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=True, qdepth=8,
                             read_percentage=100, time=30).start()
        l.append(a)

    with pytest.warns(UserWarning, match="ioworker host ERROR -1: init fail in pyx"):
        for a in l:
            r = a.close()


@pytest.mark.parametrize("repeat", range(10))
def test_ioworker_stress_multiple_small(nvme0n1, repeat, verify):
    l = []
    for i in range(16):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=True, qdepth=8,
                             read_percentage=100, time=30).start()
        l.append(a)

    for a in l:
        r = a.close()


def test_ioworker_longtime(nvme0, nvme0n1, verify):
    nvme0n1.format(512)

    # fill some data first
    a = nvme0n1.ioworker(io_size=256, lba_align=256,
                         lba_random=True, qdepth=64,
                         read_percentage=0, time=60).start().close()

    l = []
    for i in range(16):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=True, qdepth=64,
                             read_percentage=100, time=60).start()
        l.append(a)

    for a in l:
        r = a.close()


def test_ioworker_changing_ps(nvme0, nvme0n1):
    orig_ps = nvme0.getfeatures(0x2).waitdone()
    
    with nvme0n1.ioworker(io_size=256, 
                          lba_random=True,
                          read_percentage=100,
                          time=60):
        for ps in range(5):
            time.sleep(5)
            logging.info("switch to PS %d" % ps)
            nvme0.setfeatures(0x2, cdw11=ps).waitdone()
            p = nvme0.getfeatures(0x2).waitdone()
            time.sleep(5)

    nvme0.setfeatures(0x2, cdw11=orig_ps).waitdone()

    
@pytest.mark.parametrize("lba_size", [4096, 512, 4096, 512])
def test_namespace_change_format(nvme0, lba_size):
    # format to another lba format
    nvme0n1 = d.Namespace(nvme0)
    nvme0n1.format(lba_size)

    # close and re-create the namespace because the lba format is changed
    nvme0n1.close()
    nvme0n1 = d.Namespace(nvme0)
    nvme0n1.verify_enable()

    l = []
    for i in range(2):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             lba_random=True, qdepth=16,
                             read_percentage=100, time=10).start()
        l.append(a)

    for a in l:
        r = a.close()

    nvme0n1.close()


def test_issue65(nvme0, nvme0n1, subsystem):
    io = []
    for qpair in range(16):
        io.append(nvme0n1.ioworker(io_size=1, lba_random=True,
                                   read_percentage=0,
                                   qdepth=1023,
                                   time=1000).start())
    time.sleep(55)
    subsystem.poweroff()
    for i in io:
        i.close()
        
    time.sleep(1)
    subsystem.poweron()
    nvme0.reset()

    
def test_ioworker_invalid_io_size_fw_debug_mode(nvme0, nvme0n1):
    # format to clear all data before test
    nvme0n1.format(512)

    assert nvme0.mdts//512 == 256
    nvme0n1.ioworker(io_size=nvme0.mdts//512, lba_align=64,
                     lba_random=False, qdepth=4, fw_debug=True, 
                     read_percentage=100, time=2).start().close()

    with pytest.warns(UserWarning, match="ioworker device"):
        nvme0n1.ioworker(io_size=nvme0.mdts//512+1, lba_align=64,
                         lba_random=False, qdepth=4,
                         read_percentage=100, time=2).start().close()


