import time
import pytest
import logging

import nvme as d

@pytest.mark.parametrize("repeat", range(1000))
def test_quarch_dirty_power_cycle(nvme0, nvme0n1, subsystem, buf, verify, repeat):
    # verify feature is enabled
    assert verify

    # get the unsafe shutdown count before test
    nvme0.getlogpage(2, buf, 512).waitdone()
    orig_unsafe_count = buf.data(159, 144)
    logging.info("unsafe shutdowns: %d" % orig_unsafe_count)

    # 128K sequential write
    cmdlog_list = [None]*1000
    w = nvme0n1.ioworker(io_size=256, lba_random=False,
                         read_percentage=0, lba_start=0,
                         qdepth=512, time=10,
                         output_cmdlog_list=cmdlog_list).start()

    # sudden power loss before the ioworker end
    time.sleep(5)
    subsystem.poweroff()

    # wait ioworker finish and get its IO count
    io_count = w.close().io_count_write

    # power on
    subsystem.poweron()
    subsystem.reset()
    
    # list last commands
    logging.info(cmdlog_list[:10])
    logging.info(cmdlog_list[-10:])

    # verify unsafe shutdown count
    nvme0.getlogpage(2, buf, 512).waitdone()
    unsafe_count = buf.data(159, 144)
    logging.info("unsafe shutdowns: %d" % unsafe_count)
    assert unsafe_count = orig_unsafe_count+1
    
    # verify written data by read
    with nvme0n1.ioworker(io_size=256, lba_random=False,
                          read_percentage=100, lba_start=0, 
                          qdepth=512, io_count=io_count):
        pass

