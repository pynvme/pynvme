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

from nvme import *


class PRPList(Buffer):
    buf_list = {}
    
    def __setitem__(self, index, buf: Buffer):
        """insert buffer PRP to PRP List"""
        addr = buf.phys_addr
        logging.debug("insert buffer 0x%lx at %d" % (addr, index))
        assert index < 4096/8, "4K PRP List contains 512 PRP entries only"
        self.buf_list[index] = buf

        # fill PRP into PRP List
        for i, b in enumerate(addr.to_bytes(8, byteorder='little')):
            super(PRPList, self).__setitem__(index*8 + i, b) 

            
class IOSQ(object):
    """I/O Submission Queue"""
    
    id = 0
    ctrlr = None
    queue = None
    
    def __init__(self, ctrlr, qid, qsize, prp1, pc=True, cqid=None, qprio=0, nvmsetid=0):
        """create IO submission queue
        
        # Parameters
            ctrlr (Controller):
            qid (int):
            qsize (int): 1based value
            prp1 (Buffer, PRPList): the location of the queue
            cqid (int): 
            qprio (int): 
            nvmsetid (int): 

        """

        if cqid is None:
            cqid = qid

        # 1base to 0base
        qsize -= 1

        assert qid < 64*1024
        assert qid >= 0
        assert cqid < 64*1024
        assert cqid >= 0
        assert qsize < 64*1024
        assert qsize >= 0
        assert qprio < 4
        
        def create_io_sq_cpl(cdw0, status1):
            if status1>>1:
                logging.info("create io sq fail: %d" % qid)
            else:
                self.id = qid
                self.queue = prp1

        self.ctrlr = ctrlr
        ctrlr.send_cmd(0x01, prp1,
                       cdw10 = (qid|(qsize<<16)),
                       cdw11 = (pc|(qprio<<1)|(cqid<<16)),
                       cdw12 = nvmsetid, 
                       cb = create_io_sq_cpl).waitdone()

    def __setitem__(self, index, cmd: []):
        """insert command 16 dwords to the queue"""
        pass
        
    def delete(self, qid=None):
        def delete_io_sq_cpl(cdw0, status1):
            if status1>>1:
                logging.info("delete io sq fail: %d" % qid)
            else:
                self.id = 0

        if qid == None:
            qid = self.id

        logging.debug("delete sqid %d" % qid)
        if qid != 0:
            self.ctrlr.send_cmd(0x00,
                                cdw10 = qid,
                                cb = delete_io_sq_cpl).waitdone()

            
class IOCQ(object):
    """I/O Completion Queue"""
    
    id = 0
    ctrlr = None
    queue = None
    
    def __init__(self, ctrlr, qid, qsize, prp1, pc=True, iv=0, ien=False):
        """create IO completion queue
        
        # Parameters
            ctrlr (Controller):
            qid (int):
            qsize (int): 1based value
            prp1 (Buffer, PRPList):
            iv (int, None): interrupt vector

        """
        
        # 1base to 0base
        qsize -= 1

        assert qid < 64*1024
        assert qid >= 0
        assert qsize < 64*1024
        assert qsize >= 0
        assert iv < 2048, "a maximum of 2048 vectors are used"
        
        def create_io_cq_cpl(cdw0, status1):
            if status1>>1:
                logging.info("create io cq fail: %d" % qid)
            else:
                self.id = qid
                self.queue = prp1

        self.ctrlr = ctrlr
        ctrlr.send_cmd(0x05, prp1,
                       cdw10 = (qid|(qsize<<16)),
                       cdw11 = (pc|(ien<<1)|(iv<<16)),
                       cb = create_io_cq_cpl).waitdone()
        
    def delete(self, qid=None):
        def delete_io_cq_cpl(cdw0, status1):
            if status1>>1:
                logging.info("delete io cq fail: %d" % qid)
            else:
                self.id = 0

        if qid is None:
            qid = self.id
            
        logging.debug("delete cqid %d" % qid)
        if qid != 0:
            self.ctrlr.send_cmd(0x04,
                                cdw10 = qid,
                                cb = delete_io_cq_cpl).waitdone()

        
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

    # Invalid Queue Identifier
    with pytest.warns(UserWarning, match="ERROR status: 01/08"):
        cq = IOCQ(nvme0, 5, 5, buf, iv=2047, ien=True)

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
    buf_cq = Buffer(4096*pgsz)
    cq = IOCQ(nvme0, 4, 5, buf_cq)
    cq.delete()

    
def test_create_delete_iocq_non_contig(nvme0):
    prp_list = PRPList()
    prp_list[0] = Buffer()
    prp_list[1] = Buffer()
    
    cq = IOCQ(nvme0, 4, 5, prp_list, pc=False)
    cq.delete()
    

def test_create_delete_iosq(nvme0):
    buf_cq = Buffer(4096)
    cq = IOCQ(nvme0, 4, 5, buf_cq)

    buf_sq = Buffer(4096)

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
    

def test_send_cmd_write_zeroes(nvme0):
    pass


def test_reap_cpl_write_zeroes(nvme0):
    pass


@pytest.mark.parametrize("count", [1, 2, 8, 500, 512])
def test_prp_and_prp_list(count):
    l = PRPList()
    for i in range(count):
        l[i] = Buffer()


def test_prp_and_prp_list_invalid():
    l = PRPList()
    with pytest.raises(AssertionError):
        l[512] = Buffer()
        
