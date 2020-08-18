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
    

@pytest.mark.parametrize("repeat", range(10))
def test_reset_within_ioworker(nvme0, subsystem, pcie, repeat):
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
    orig_unsafe_count = power_cycle_count()
    logging.info("power cycle count: %d" % orig_unsafe_count)

    # 128K random write
    cmdlog_list = [None]*1000
    with nvme0n1.ioworker(io_size=256,
                          lba_random=True,
                          read_percentage=30,
                          region_end=region_end,
                          time=10,
                          qdepth=qdepth, 
                          output_cmdlog_list=cmdlog_list):
        # sudden power loss before the ioworker end
        time.sleep(5)
        
        # disable cc.en and wait for csts.rdy
    if 0:
        nvme0[0x14] = 0
        t = time.time()
        while not (nvme0[0x1c]&0x1) == 0:
            if time.time()-t > 10:
                logging.error("csts.rdy timeout 10s after cc.en=0")
                assert False

    subsystem.reset()
    nvme0.reset()

    # verify data in cmdlog_list
    time.sleep(5)
    assert True == nvme0n1.verify_enable(True)
    logging.info(cmdlog_list[-10:])
    read_buf = d.Buffer(256*512)
    qpair = d.Qpair(nvme0, 10)
    for cmd in cmdlog_list:
        slba = cmd[0]
        nlba = cmd[1]
        op = cmd[2]
        if nlba:
            def read_cb(cdw0, status1):
                nonlocal _slba
                if status1>>1:
                    logging.info("slba %d, 0x%x, _slba 0x%x, status 0x%x" % \
                                 (slba, slba, _slba, status1>>1))
                    
            logging.debug("verify slba %d, nlba %d" % (slba, nlba))
            _nlba = nlba//16
            for i in range(16):
                _slba = slba+i*_nlba
                nvme0n1.read(qpair, read_buf, _slba, _nlba, cb=read_cb).waitdone()
            
            # re-write to clear CRC mismatch
            nvme0n1.write(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
    qpair.delete()
    nvme0n1.close()

    # verify unsafe shutdown count
    unsafe_count = power_cycle_count()
    logging.info("power cycle count: %d" % unsafe_count)
    assert unsafe_count == orig_unsafe_count
    
