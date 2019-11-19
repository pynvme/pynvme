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
    pass


class IOCQ(object):
    """I/O Completion Queue"""
    
    id = 0
    ctrlr = None
    
    def __init__(self, ctrlr, qid, qsize, data, iv=0, ien=False):
        """create IO completion queue
        
        # Parameters
            ctrlr (Controller):
            qid (int):
            qsize (int):
            data (Buffer, PRPList):
            iv (int): interrupt vector
            ien (bool): interrupt enabled

        """

        logging.info("create io cq")
        assert qid < 64*1024
        assert qsize < 64*1024
        assert iv < 2048, "a maximum of 2048 vectors are used"
        
        def _cb(cdw0, status1):
            logging.info("create io cq completed")

        self.id = qid
        self.ctrlr = ctrlr
        pc = True if type(data) is Buffer else False
        ctrlr.send_cmd(0x05, data,
                       cdw10 = (qid|(qsize<<16)),
                       cdw11 = (pc|(ien<<1)|(iv<<16)),
                       cb = _cb).waitdone()

    def __del__(self):
        def _cb(cdw0, status1):
            logging.info("delete io cq completed")
            
        self.ctrlr.send_cmd(0x04,
                            cdw10 = self.id,
                            cb = _cb).waitdone()

        
def test_create_delete_iocq(nvme0):
    buf = Buffer(512)
    cq = IOCQ(nvme0, 0, 0, buf)
    del cq


def test_create_delete_iocq_non_contig(nvme0):
    pass


def test_create_delete_iosq(nvme0):
    pass


def test_send_cmd_write_zeroes(nvme0):
    pass


def test_reap_cpl_write_zeroes(nvme0):
    pass


def test_prp_and_prp_list(nvme0):
    pass

