import time
import pytest
import logging

import nvme as d

@pytest.mark.parametrize("repeat", range(100))
def test_quarch_dirty_power_cycle(nvme0, nvme0n1, subsystem, buf, verify, repeat):
    # get the unsafe shutdown count before test
    nvme0.getlogpage(2, buf, 512).waitdone()
    orig_unsafe_count = buf.data(159, 144)
    logging.info("unsafe shutdowns: %d" % orig_unsafe_count)

    # 128K sequential write
    cmdlog_list = [None]*1000
    with nvme0n1.ioworker(io_size=256, lba_random=False,
                          read_percentage=0, lba_start=0,
                          qdepth=1024, time=30,
                          output_cmdlog_list=cmdlog_list):
        # sudden power loss before the ioworker end
        time.sleep(5)
        subsystem.poweroff()

    # power on
    time.sleep(5)
    subsystem.poweron()
    time.sleep(0)
    subsystem.reset()

    # verify unsafe shutdown count
    logging.info(cmdlog_list[:10])
    nvme0.getlogpage(2, buf, 512).waitdone()
    unsafe_count = buf.data(159, 144)
    logging.info("unsafe shutdowns: %d" % unsafe_count)
    assert unsafe_count == orig_unsafe_count+1

    with nvme0n1.ioworker(io_size=256, lba_random=False,
                          read_percentage=100, lba_start=0, time=10, 
                          qdepth=1024, io_count=cmdlog_list[-1][0]):
        pass
    
    # verify data in cmdlog_list
    assert verify
    read_buf = d.Buffer(256*512)
    qpair = d.Qpair(nvme0, 1024)
    for cmd in cmdlog_list:
        slba = cmd[0]
        nlba = cmd[1]
        if nlba:
            def read_cb(cdw0, status1):
                nonlocal slba
                if status1>>1:
                    logging.info("slba 0x%x, status 0x%x" % (slba, status1>>1))
            #logging.info("verify slba 0x%x, nlba %d" % (slba, nlba))
            nvme0n1.read(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()

