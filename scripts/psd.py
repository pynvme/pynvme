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

from nvme import *


class PRP(Buffer):
    pass


class PRPList(PRP):
    def __init__(self):
        self.prp_per_list = 4096//8
        self.buf_list = [None]*self.prp_per_list

    def __setitem__(self, index, buf: PRP):
        """insert buffer PRP to PRP List"""
        addr = buf.phys_addr
        logging.debug("insert buffer 0x%lx at %d" % (addr, index))
        assert index < self.prp_per_list, "4K PRP List contains 512 PRP entries only"
        self.buf_list[index] = buf

        # fill PRP into PRP List
        for i, b in enumerate(addr.to_bytes(8, byteorder='little')):
            super(PRPList, self).__setitem__(index*8 + i, b)

    def __getitem__(self, index):
        assert index < self.prp_per_list, "4K PRP List contains 512 PRP entries only"
        return self.buf_list[index]

    def find_buffer_by_offset(self, offset, start):
        """find the buffer of the non-contiguous queue contains the offset"""

        first_index = self.offset//8
        for buf in self.buf_list[first_index : self.prp_per_list]:
            assert buf is not None
            if isinstance(buf, PRPList):
                # the last entry could be another PRPList
                assert buf == self.buf_list[self.prp_per_list - 1]
                return buf.find_buffer_by_offset(offset, start)
            else:
                orig_start = start
                start += (len(buf)-buf.offset)
                if start > offset:
                    return buf, buf.offset+offset-orig_start


class SQE(list):
    _buf_list = []

    def __init__(self, *arg):
        assert len(arg) <= 16
        list.extend(self, [0]*16)
        for i, e in enumerate(arg):
            list.__setitem__(self, i, e)

    def __repr__(self):
        return "\n0x%08x, 0x%08x, 0x%08x, 0x%08x" \
               "\n0x%08x, 0x%08x, 0x%08x, 0x%08x" \
               "\n0x%08x, 0x%08x, 0x%08x, 0x%08x" \
               "\n0x%08x, 0x%08x, 0x%08x, 0x%08x" % \
               (self[0], self[1], self[2], self[3], \
                self[4], self[5], self[6], self[7], \
                self[8], self[9], self[10], self[11], \
                self[12], self[13], self[14], self[15])
        
    @property
    def opc(self):
        return self[0]&0xff

    @opc.setter
    def opc(self, opc):
        self[0] = (self[0]&0xffffff00) | opc

    @property
    def cid(self):
        return self[0]>>16

    @cid.setter
    def cid(self, cid):
        self[0] = (self[0]&0xffff) | (cid<<16)

    @property
    def nsid(self):
        return self[1]

    @nsid.setter
    def nsid(self, nsid):
        self[1] = nsid

    @property
    def prp1(self):
        return (self[7]<<32) | self[6]

    @prp1.setter
    def prp1(self, buf: Buffer):
        prp = buf.phys_addr
        self[6] = prp&0xffffffff
        self[7] = (prp>>32)&0xffffffff
        self._buf_list.append(buf)

    @property
    def prp2(self):
        return (self[9]<<32) | self[8]

    @prp2.setter
    def prp2(self, buf: Buffer):
        prp = buf.phys_addr
        self[8] = prp&0xffffffff
        self[9] = (prp>>32)&0xffffffff
        self._buf_list.append(buf)


class CQE(list):
    def __init__(self, arg):
        assert len(arg) == 4
        for e in arg:
            list.append(self, e)

    def __repr__(self):
        return "0x%08x, 0x%08x, 0x%08x, 0x%08x" % \
            (self[0], self[1], self[2], self[3])
        
    @property
    def cdw0(self):
        return self[0]

    @property
    def sqhd(self):
        return self[2]&0xffff

    @property
    def sqid(self):
        return (self[2]>>16)&0xffff

    @property
    def cid(self):
        return self[3]&0xffff

    @property
    def p(self):
        return (self[3]>>16)&0x1

    @property
    def status(self):
        return (self[3]>>17)&0x8fff

    @property
    def sc(self):
        return (self[3]>>17)&0xff

    @property
    def sct(self):
        return (self[3]>>25)&0x7

    @property
    def crd(self):
        return (self[3]>>28)&0x3

    @property
    def m(self):
        return (self[3]>>30)&0x1

    @property
    def dnr(self):
        return (self[3]>>31)&0x1


class IOSQ(object):
    """I/O Submission Queue"""

    id = 0
    ctrlr = None
    queue = None
    sqe_list = None

    def __init__(self, ctrlr, qid, qsize, prp1, pc=True, cqid=None, qprio=0, nvmsetid=0):
        """create IO submission queue

        # Parameters
            ctrlr (Controller):
            qid (int):
            qsize (int): 1based value
            prp1 (PRP, PRPList): the location of the queue
            cqid (int):
            qprio (int):
            nvmsetid (int):

        """

        # some id cq
        status = 0
        if cqid is None:
            cqid = qid

        assert qid < 64*1024 and qid >= 0
        assert cqid < 64*1024 and cqid >= 0
        assert qsize <= 64*1024 and qsize > 0
        assert qprio < 4 and qprio >= 0

        def create_io_sq_cpl(cdw0, status1):
            nonlocal status; status = status1>>1

        self.ctrlr = ctrlr
        ctrlr.send_cmd(0x01, prp1,
                       cdw10 = (qid|((qsize-1)<<16)),
                       cdw11 = (pc|(qprio<<1)|(cqid<<16)),
                       cdw12 = nvmsetid,
                       cb = create_io_sq_cpl).waitdone()
        if not status:
            self.id = qid
            self.queue = prp1
            self.sqe_list = [None]*qsize

    def __getitem__(self, index):
        assert index < len(self.sqe_list)
        return self.sqe_list[index]
    
    def __setitem__(self, index, cmd: SQE):
        """insert 16-dword SQE to the queue"""

        assert len(cmd) == 16
        assert index < len(self.sqe_list)

        # track the cmd in the queue
        self.sqe_list[index] = cmd

        # locate the queue buffer
        if isinstance(self.queue, PRPList):
            # find the PRP entry in non-contig queue
            buf, offset = self.queue.find_buffer_by_offset(index*64, 0)
            index = offset/64
        else:
            buf = self.queue

        assert isinstance(buf, PRP)
        for i, dword in enumerate(cmd):
            for j, b in enumerate(dword.to_bytes(4, byteorder='little')):
                buf[index*64 + i*4 + j] = b

    @property
    def tail(self):
        return self.ctrlr[0x1000+2*self.id*4]

    @tail.setter
    def tail(self, tail):
        logging.debug(tail)
        self.ctrlr[0x1000+2*self.id*4] = tail

    def delete(self, qid=None):
        if qid == None:
            qid = self.id

        logging.debug("delete sqid %d" % qid)
        if qid != 0:
            self.ctrlr.send_cmd(0x00, cdw10=qid).waitdone()


class IOCQ(object):
    """I/O Completion Queue"""

    id = 0
    ctrlr = None
    queue = None
    qsize = 0

    def __init__(self, ctrlr, qid, qsize, prp1, pc=True, iv=0, ien=False):
        """create IO completion queue

        # Parameters
            ctrlr (Controller):
            qid (int):
            qsize (int): 1based value
            prp1 (Buffer, PRPList):
            iv (int, None): interrupt vector

        """

        status = 0

        assert qid < 64*1024 and qid >= 0
        assert qsize < 64*1024 and qsize > 0

        def create_io_cq_cpl(cdw0, status1):
            nonlocal status; status = status1>>1

        self.ctrlr = ctrlr
        ctrlr.send_cmd(0x05, prp1,
                       cdw10 = (qid|((qsize-1)<<16)),
                       cdw11 = (pc|(ien<<1)|(iv<<16)),
                       cb = create_io_cq_cpl).waitdone()

        if not status:
            self.id = qid
            self.queue = prp1
            self.qsize = qsize

    def __getitem__(self, index):
        """get 4-dword CQE from the queue"""

        assert index < self.qsize

        cpl = [0]*4
        buf = self.queue
        if isinstance(buf, PRPList):
            # find the PRP entry in non-contig queue
            buf, offset = self.queue.find_buffer_by_offset(index*16, 0)
            index = offset/16
        else:
            buf = self.queue

        assert isinstance(buf, PRP)
        for i in range(4):
            cpl[i] = buf.data(index*16 + i*4 + 3, index*16 + i*4)

        assert len(cpl) == 4
        return CQE(cpl)

    @property
    def head(self):
        return self.ctrlr[0x1000+(2*self.id+1)*4]

    @head.setter
    def head(self, head):
        self.ctrlr[0x1000+(2*self.id+1)*4] = head

    def delete(self, qid=None):
        if qid is None:
            qid = self.id

        logging.debug("delete cqid %d" % qid)
        if qid != 0:
            self.ctrlr.send_cmd(0x04, cdw10=qid).waitdone()


def test_create_delete_iocq(nvme0):
    buf = Buffer(4096)

    cq1 = IOCQ(nvme0, 5, 5, buf)

    # Invalid Queue Identifier
    with pytest.warns(UserWarning, match="ERROR status: 01/01"):
        cq2 = IOCQ(nvme0, 5, 10, buf)

    cq1.delete()

    # Invalid Queue Size
    with pytest.warns(UserWarning, match="ERROR status: 01/02"):
        cq = IOCQ(nvme0, 5, 1, buf)

    # Invalid Queue Identifier
    with pytest.warns(UserWarning, match="ERROR status: 01/01"):
        cq = IOCQ(nvme0, 0, 5, buf)

    # Invalid interrupt vector
    with pytest.warns(UserWarning, match="ERROR status: 01/08"):
        cq = IOCQ(nvme0, 5, 5, buf, iv=2047, ien=True)

    # Invalid interrupt vector
    with pytest.warns(UserWarning, match="ERROR status: 01/08"):
        cq = IOCQ(nvme0, 5, 5, buf, iv=2049, ien=True)

    cq = IOCQ(nvme0, 5, 5, buf, iv=5)
    with pytest.warns(UserWarning, match="ERROR status: 01/01"):
        cq.delete(4)
    cq.delete()

    cq = IOCQ(nvme0, 5, 5, buf, iv=5, ien=True)
    cq.delete()

    cq1 = IOCQ(nvme0, 5, 5, buf)
    cq2 = IOCQ(nvme0, 6, 5, buf)
    cq3 = IOCQ(nvme0, 7, 5, buf)
    cq3.delete()
    cq2.delete()
    cq1.delete()


@pytest.mark.parametrize("pgsz", [1, 2, 3, 10, 256, 512, 1024])
def test_create_delete_iocq_large(nvme0, pgsz):
    buf_cq = PRP(4096*pgsz)
    cq = IOCQ(nvme0, 4, 5, buf_cq)
    cq.delete()


def test_create_delete_iocq_non_contig(nvme0):
    prp_list = PRPList()
    prp_list[0] = PRP()
    prp_list[1] = PRP()

    cq = IOCQ(nvme0, 4, 5, prp_list, pc=False)
    cq.delete()


def test_create_delete_iosq(nvme0):
    buf_cq = PRP(4096)
    cq = IOCQ(nvme0, 4, 5, buf_cq)

    buf_sq = PRP(4096)

    # Completion Queue Invalid
    with pytest.warns(UserWarning, match="ERROR status: 01/00"):
        sq = IOSQ(nvme0, 4, 10, buf_sq, cqid=1)

    with pytest.warns(UserWarning, match="ERROR status: 01/01"):
        sq = IOSQ(nvme0, 400, 10, buf_sq, cqid=4)

    with pytest.warns(UserWarning, match="ERROR status: 01/02"):
        sq = IOSQ(nvme0, 4, 1, buf_sq, cqid=4)

    sq = IOSQ(nvme0, 5, 10, buf_sq, cqid=4)
    with pytest.warns(UserWarning, match="ERROR status: 01/01"):
        sq.delete(4)

    # Invalid Queue Deletion
    with pytest.warns(UserWarning, match="ERROR status: 01/0c"):
        cq.delete()

    sq.delete()
    cq.delete()


def test_send_single_cmd(nvme0):
    cq = IOCQ(nvme0, 1, 10, PRP())
    sq = IOSQ(nvme0, 1, 10, PRP(), cqid=1)

    # first cmd, invalid namespace
    sq[0] = [4] + [0]*15
    sq.tail = 1
    time.sleep(0.1)
    status = (cq[0][3]>>17)&0x7ff
    assert status == 0x000b

    sq.delete()
    cq.delete()


@pytest.mark.parametrize("count", [1, 2, 8, 500, 512])
def test_prp_and_prp_list(count):
    l = PRPList()
    for i in range(count):
        l[i] = Buffer()


def test_prp_and_prp_list_with_offset():
    p = PRP()
    p.offset = 0x20

    l = PRPList()
    l.offset = 0x40
    l[8] = p

    p = PRP()
    p.offset = 0x30
    l[9] = p

    assert l.phys_addr&0x7 == 0
    assert l.phys_addr&0xfff == 0x40
    assert l[8].phys_addr&0xfff == 0x20
    assert l[9].phys_addr&0xfff == 0x30


def test_prp_and_prp_list_invalid():
    l = PRPList()
    with pytest.raises(AssertionError):
        l[512] = Buffer()

        
@pytest.mark.parametrize("qdepth", [7, 2, 3, 4, 5, 10, 16, 17, 31])
def test_send_cmd_different_qdepth(nvme0, qdepth):
    cq = IOCQ(nvme0, 4, qdepth, PRP())
    sq = IOSQ(nvme0, 4, qdepth, PRP(), cqid=4)

    # once again: first cmd, invalid namespace
    for i in range(qdepth*3 + 3):
        index = (i+1)%qdepth
        sq[index-1] = [0, 1] + [0]*14
        sq.tail = index
        time.sleep(0.01)
        assert (cq[index-1][3]>>17) == 0
        assert (cq[index-1][2]&0xffff) == index
        cq.head = index

    sq.delete()
    cq.delete()
    

def test_send_cmd_2sq_1cq(nvme0):
    cq = IOCQ(nvme0, 1, 10, PRP())
    sq1 = IOSQ(nvme0, 1, 10, PRP(), cqid=1)
    sq2 = IOSQ(nvme0, 2, 16, PRP(), cqid=1)

    cdw = SQE(0, 0, 0)
    cdw.nsid = 1  # namespace id
    cdw.cid = 222
    sq1[0] = cdw

    sqe = SQE(*cdw)
    assert sqe[1] == 1
    sqe.cid = 111
    sq2[0] = sqe
    sq2.tail = 1
    time.sleep(0.1)
    sq1.tail = 1
    time.sleep(0.1)

    sq1.delete()
    sq2.delete()
    cq.delete()

        
def test_psd_write_2sq_1cq_prp_list(nvme0, subsystem):
    # cqid: 1, PC, depth: 120
    cq = IOCQ(nvme0, 1, 120, PRP(4096))

    # create two SQ, both use the same CQ
    # sqid: 3, depth: 16
    sq3 = IOSQ(nvme0, 3, 16, PRP(), cqid=1)
    # sqid: 5, depth: 100, so need 2 pages of memory
    sq5 = IOSQ(nvme0, 5, 64*64, PRP(4096*64), cqid=1)

    # IO command templates: opcode and namespace
    write_cmd = SQE(1, 1)
    read_cmd = SQE(2, 1)

    # write in sq3, lba1-lba2, 1 page, aligned
    w1 = SQE(*write_cmd)
    write_buf = PRP(ptype=32, pvalue=0xaaaaaaaa)
    w1.prp1 = write_buf
    w1[10] = 1
    w1[12] = 1 # 0based
    w1.cid = 0x123
    sq3[0] = w1
    sq3.tail = 1

    # add some delay, so ssd should finish w1 before w2
    time.sleep(0.1)

    # write in sq5, lba5-lba16, 2 page, non aligned
    w2 = SQE(*write_cmd)
    buf1 = PRP(ptype=32, pvalue=0xbbbbbbbd)
    buf1.offset = 2048
    w2.prp1 = buf1
    w2.prp2 = PRP(ptype=32, pvalue=0xcccccccc)
    w2[10] = 5
    w2[12] = 11 # 0based
    w2.cid = 0x567
    sq5[0] = w2
    sq5.tail = 1

    # cqe for w1
    while CQE(cq[0]).p == 0: pass
    cqe = CQE(cq[0])
    assert cqe.cid == 0x123
    assert cqe.sqid == 3
    assert cqe.sqhd == 1
    cq.head = 1

    # cqe for w2
    while CQE(cq[1]).p == 0: pass
    cqe = CQE(cq[1])
    assert cqe.cid == 0x567
    assert cqe.sqid == 5
    assert cqe.sqhd == 1
    cq.head = 2

    # read in sq3, lba0-lba23, 3 page with PRP list
    r1 = SQE(*read_cmd)
    read_buf = [PRP() for i in range(3)]
    r1.prp1 = read_buf[0]
    prp_list = PRPList()
    prp_list[0] = read_buf[1]
    prp_list[1] = read_buf[2]
    r1.prp2 = prp_list
    r1[10] = 0
    r1[12] = 23 # 0based
    sq3[1] = r1
    sq3.tail = 2

    # verify read data
    while cq[2].p == 0: pass
    cq.head = 3
    assert read_buf[0].data(0xfff, 0xffc) == 0xbbbbbbbd
    assert read_buf[2].data(3, 0) == 0xcccccccc
    assert read_buf[2].data(0x1ff, 0x1fc) == 0xcccccccc

    # delete all sq/cq
    sq3.delete()
    sq5.delete()
    cq.delete()


def test_iocq_prplist():
    prp_list = PRPList()
    p = PRP()
    p.offset = 4096-64
    prp_list[510] = p
    prp_list.offset = 4096-16

    prp_list2 = PRPList()
    prp_list[511] = prp_list2

    prp_list2[0] = PRP()
    prp_list2[1] = PRP()
    prp_list2[2] = PRP()
    prp_list2[3] = PRP()

    buffer, offset = prp_list.find_buffer_by_offset(0, 0)
    assert buffer == p
    assert offset == p.offset

    buffer, offset = prp_list.find_buffer_by_offset(5*16, 0)
    assert buffer == prp_list2[0]
    assert offset == 16

    buffer, offset = prp_list.find_buffer_by_offset(1000*16, 0)
    assert buffer == prp_list2[3]
    assert offset == 3648


def test_psd_with_qpair(nvme0):
    # do not mix psd IO queues with SPDK qpairs in the same test script
    qpair = Qpair(nvme0, 16)
    buf_cq = PRP(4096)
    qid = qpair.sqid
    # Invalid Queue Identifier: the id is occupied
    with pytest.warns(UserWarning, match="ERROR status: 01/01"):
        cq = IOCQ(nvme0, qid, 5, buf_cq)
    cq.delete()
    qpair.delete()

    cq = IOCQ(nvme0, qid, 5, buf_cq)
    # the qid 1 was occupied by psd IOCQ first
    with pytest.raises(QpairCreationError):
        qpair = Qpair(nvme0, 16)
    cq.delete()


def test_write_before_power_cycle(nvme0, subsystem):
    cq = IOCQ(nvme0, 1, 128, PRP(2*1024))
    sq = IOSQ(nvme0, 1, 128, PRP(8*1024), cqid=1)

    #burst write
    for i in range(127):
        cmd = SQE(1, 1)
        buf = PRP(512, ptype=32, pvalue=i)
        cmd.prp1 = buf
        cmd[10] = i
        sq[i] = cmd

    # write 127 512byte at one shot
    sq.tail = 127

    #not to wait commands completion
    # while CQE(cq[126]).p == 0: pass
    # cq.head = 0

    # sq.delete()
    # cq.delete()

    # power off immediately without completion of the sub process
    subsystem.power_cycle(10)
    nvme0.reset()

    # read and check
    cq = IOCQ(nvme0, 2, 16, PRP())
    sq = IOSQ(nvme0, 2, 16, PRP(), cqid=2)

    cmd = SQE(2, 1)
    buf_read = PRP()
    cmd.prp1 = buf_read
    cmd[10] = 126
    sq[0] = cmd
    sq.tail = 1
    while CQE(cq[0]).p == 0: pass
    cq.head = 1
    print(buf_read.dump(32))

    sq.delete()
    cq.delete()


def test_invalid_sq_doorbell(nvme0):
    cq = IOCQ(nvme0, 4, 16, PRP())
    sq1 = IOSQ(nvme0, 4, 16, PRP(), cqid=4)

    write_cmd = SQE(1, 1)
    write_cmd.prp1 = PRP()
    prp_list = PRPList()
    prp_list[0] = PRP()
    prp_list[1] = PRP()
    prp_list[2] = PRP()
    write_cmd.prp2 = prp_list
    write_cmd[10] = 0
    write_cmd[12] = 31
    write_cmd.cid = 123

    sq1[0] = write_cmd
    write_cmd.cid = 567
    sq1.tail = 17

    # wait for the controller to respond the error
    time.sleep(0.1)
    with pytest.warns(UserWarning, match="AER notification is triggered: 0x10100"):
        nvme0.getfeatures(7).waitdone()
    sq1.delete()
    cq.delete()
    

def test_write_read_verify(nvme0, nvme0n1):
    cq = IOCQ(nvme0, 1, 1024, PRP(1024*64))
    sq = IOSQ(nvme0, 1, 1024, PRP(1024*64), cqid=1)

    write_cmd = SQE(1, 1)
    write_cmd[12] = 7  # 4K write
    buf_list = []
    for i in range(10):
        buf = PRP(ptype=32, pvalue=0x01010101*i)
        buf_list.append(buf)
        write_cmd.prp1 = buf
        write_cmd.cid = i
        write_cmd[10] = i
        sq[i] = write_cmd
    sq.tail = 10
    
    while cq[9].p == 0: pass
    sq.delete()
    cq.delete()
    
    # read after reset with outstanding writes
    cq = IOCQ(nvme0, 1, 1024, PRP(1024*64))
    sq = IOSQ(nvme0, 1, 1024, PRP(1024*64), cqid=1)

    read_cmd = SQE(2, 1)
    read_cmd[12] = 7  # 4K read
    buf_list = []
    for i in range(10):
        buf = PRP()
        buf_list.append(buf)
        read_cmd.prp1 = buf
        read_cmd.cid = i
        read_cmd[10] = i
        sq[i] = read_cmd
    sq.tail = 10

    while cq[9].p == 0: pass
    for i in range(10):
        logging.info(cq[i].cid)
        assert buf_list[cq[i].cid][0] == cq[i].cid
    sq.delete()
    cq.delete()


