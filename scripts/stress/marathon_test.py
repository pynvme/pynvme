import pytest
import nvme as d

import time
import logging


def test_write_and_read_to_eol(nvme0, subsystem, nvme0n1: d.Namespace, verify):
    assert verify
    
    # format drive
    nvme0n1.format()
    lba_count = nvme0n1.id_data(7, 0)

    # test for PE cycles
    for i in range(3000):
        logging.info(f"loop {i} start")

        # write 1 pass of whole drive
        io_size = 64*1024/512  # 64KB
        write_start = time.time()
        nvme0n1.ioworker(io_size, io_size, False, 0, io_count=lba_count//io_size).start().close()
        write_duration = time.time()-write_start
        logging.info("full drive write %d seconds" % write_duration)
        assert write_duration < 1800

        # power cycle
        subsystem.power_cycle(15)
        
        # read part of drive
        read_time = 1800-write_duration
        nvme0n1.ioworker(io_size, io_size, False, 100, read_time, region_end=lba_count//100).start().close()
        logging.info(f"loop {i} finish")
        
        # power cycle
        subsystem.power_cycle(15)
