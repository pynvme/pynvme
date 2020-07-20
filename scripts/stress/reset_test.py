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
    

@pytest.mark.parametrize("repeat", range(100))
def test_reset_within_ioworker(nvme0, repeat):
    region_end = 256*1000*1000  # 1GB
    qdepth = min(1024, 1+(nvme0.cap&0xffff))
    
    # get the unsafe shutdown count
    def power_cycle_count():
        buf = d.Buffer(4096)
        nvme0.getlogpage(2, buf, 512).waitdone()
        return buf.data(115, 112)
    
    # run the test one by one
    subsystem = d.Subsystem(nvme0)
    nvme0n1 = d.Namespace(nvme0, 1, region_end)
    assert True == nvme0n1.verify_enable(True)
    orig_unsafe_count = power_cycle_count()
    logging.info("power cycle count: %d" % orig_unsafe_count)

    # 128K random write
    cmdlog_list = [None]*1000
    with nvme0n1.ioworker(io_size=256,
                          lba_random=True,
                          read_percentage=30,
                          region_end=256*1000*1000,
                          time=10,
                          qdepth=qdepth, 
                          output_cmdlog_list=cmdlog_list):
        # sudden power loss before the ioworker end
        time.sleep(5)
        nvme0.reset()

    time.sleep(5)

    # verify data in cmdlog_list
    logging.info(cmdlog_list[-10:])
    read_buf = d.Buffer(256*512)
    qpair = d.Qpair(nvme0, 10)
    for cmd in cmdlog_list:
        slba = cmd[0]
        nlba = cmd[1]
        op = cmd[2]
        if nlba:
            def read_cb(cdw0, status1):
                nonlocal slba
                if status1>>1:
                    logging.info("slba 0x%x, status 0x%x" % (slba, status1>>1))
                    
            logging.debug("verify slba %d, nlba %d" % (slba, nlba))
            for i in range(4):
                nvme0n1.read(qpair, read_buf,
                             slba+i*nlba//4, nlba//4,
                             cb=read_cb).waitdone()
            
            # re-write to clear CRC mismatch
            nvme0n1.write(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
    qpair.delete()
    nvme0n1.close()

    # verify unsafe shutdown count
    unsafe_count = power_cycle_count()
    logging.info("power cycle count: %d" % unsafe_count)
    assert unsafe_count == orig_unsafe_count
    
