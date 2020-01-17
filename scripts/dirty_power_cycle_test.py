import time
import pytest
import logging

import nvme as d

def test_quarch_dirty_power_cycle(nvme0, nvme0n1, subsystem, buf):
    nvme0.getlogpage(2, buf, 512).waitdone()
    logging.info("unsafe shutdowns: %d" % buf.data(159, 144))

    cmdlog = [None]*15
    with nvme0n1.ioworker(io_size=255, time=10, qdepth=1023, read_percentage=0, output_cmdlog_list=cmdlog):
        time.sleep(5)
        subsystem.poweroff()

    subsystem.poweron()
    subsystem.reset()
    logging.info(cmdlog)
    with nvme0n1.ioworker(io_size=255, time=10, qdepth=1023, read_percentage=0):
        pass

    nvme0.getlogpage(2, buf, 512).waitdone()
    logging.info("unsafe shutdowns: %d" % buf.data(159, 144))
