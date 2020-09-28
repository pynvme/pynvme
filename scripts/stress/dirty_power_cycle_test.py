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


def test_precondition_format(pcie, nvme0, nvme0n1, subsystem):
    pcie.reset()
    nvme0.reset()
    subsystem.power_cycle()
    nvme0.reset()
    nvme0n1.format(512)
    

def test_quarch_dirty_power_cycle_single(nvme0, poweron=None, poweroff=None):
    region_end = 256*1000*1000  # 1GB
    qdepth = min(1024, 1+(nvme0.cap&0xffff))
    
    # get the unsafe shutdown count
    def power_cycle_count():
        buf = d.Buffer(4096)
        nvme0.getlogpage(2, buf, 512).waitdone()
        return buf.data(115, 112)
    
    # run the test one by one
    subsystem = d.Subsystem(nvme0, poweron, poweroff)
    nvme0n1 = d.Namespace(nvme0, 1, region_end)
    assert True == nvme0n1.verify_enable(True)
    orig_unsafe_count = power_cycle_count()
    logging.info("power cycle count: %d" % orig_unsafe_count)

    # 128K random write
    cmdlog_list = [None]*1000
    with nvme0n1.ioworker(io_size=256,
                          lba_random=True,
                          read_percentage=30,
                          region_end=region_end,
                          time=30,
                          qdepth=qdepth, 
                          output_cmdlog_list=cmdlog_list):
        # sudden power loss before the ioworker end
        time.sleep(10)
        subsystem.poweroff()

    # power on and reset controller
    time.sleep(5)
    subsystem.poweron()
    nvme0.reset()

    # verify data in cmdlog_list
    logging.info(cmdlog_list[-10:])
    read_buf = d.Buffer(256*512)
    qpair = d.Qpair(nvme0, 10)
    for cmd in cmdlog_list:
        slba = cmd[0]
        nlba = cmd[1]
        op = cmd[2]
        if nlba and op==1:
            def read_cb(cdw0, status1):
                nonlocal slba
                if status1>>1:
                    logging.info("slba 0x%x, status 0x%x" % (slba, status1>>1))
            #logging.info("verify slba 0x%x, nlba %d" % (slba, nlba))
            nvme0n1.read(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
            # re-write to clear CRC mismatch
            nvme0n1.write(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
    qpair.delete()
    nvme0n1.close()

    # verify unsafe shutdown count
    unsafe_count = power_cycle_count()
    logging.info("power cycle count: %d" % unsafe_count)
    assert unsafe_count == orig_unsafe_count+1

    
# define the power on/off funciton
class quarch_power:
    def __init__(self, url: str, event: str, port: int):
        self.url = url
        self.event = event
        self.port = port
        
    def __call__(self):
        import quarchpy
        logging.debug("power %s by quarch device %s on port %d" %
                      (self.event, self.url, self.port))
        pwr = quarchpy.quarchDevice(self.url)
        
        if self.port == None:
            # serial port
            if self.event == "down":
                # cut down power with data link at the same time
                pwr.sendCommand("signal:all:source 7")
            pwr.sendCommand("run:power %s" % self.event)
        else:
            # network 4-port
            if self.event == "down":
                # cut down power with data link at the same time
                pwr.sendCommand("signal:all:source 7 <%d>" % self.port)
            pwr.sendCommand("run:power %s <%d>" % (self.event, self.port))
            
        pwr.closeConnection()
        

@pytest.mark.parametrize("repeat", range(10))
def test_quarch_dirty_power_cycle_multiple(pciaddr, nvme0, repeat):
    device_list = {
        "0000:06:00.0": # pynvme's software-defined power cycle
        (None,
         None),  
        "0000:3d:00.0": # pynvme's software-defined power cycle
        (None,
         None),  
        "0000:08:00.0":
        (quarch_power("SERIAL:/dev/ttyUSB0", "up", None),
         quarch_power("SERIAL:/dev/ttyUSB0", "down", None)),
        "0000:01:00.0":
        (quarch_power("REST:192.168.1.11", "up", 4),
         quarch_power("REST:192.168.1.11", "down", 4)),
        "0000:55:00.0":
        (quarch_power("REST:192.168.1.11", "up", 1),
         quarch_power("REST:192.168.1.11", "down", 1)),
        "0000:51:00.0":
        (quarch_power("REST:192.168.1.11", "up", 3),
         quarch_power("REST:192.168.1.11", "down", 3)),
    }

    poweron, poweroff = device_list[pciaddr]
    test_quarch_dirty_power_cycle_single(nvme0, poweron, poweroff)

