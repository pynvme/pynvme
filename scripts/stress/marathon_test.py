import pytest
import nvme as d

import time
import logging


TEST_LOOPS = 3  # 3000


def test_ioworker_longtime(nvme0n1, qcount=1):
    l = []
    io_total = 0
    for i in range(qcount):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             region_start=0, region_end=256*1024*8, # 1GB space
                             lba_random=False, qdepth=16,
                             read_percentage=0, time=50*3600).start()
        l.append(a)

    for a in l:
        r = a.close()
        io_total += (r.io_count_read+r.io_count_nonread)

    logging.info("Q %d IOPS: %.3fK" % (qcount, io_total/50000/3600))

    
def test_write_and_read_to_eol(nvme0, subsystem, nvme0n1: d.Namespace, verify):
    assert verify
    
    # format drive
    nvme0n1.format(512)
    lba_count = nvme0n1.id_data(7, 0)

    # test for PE cycles
    for i in range(TEST_LOOPS):
        logging.info("loop %d start" % i)

        # write 1 pass of whole drive
        io_size = 64*1024//512  # 64KB
        write_start = time.time()
        nvme0n1.ioworker(io_size=io_size,
                         lba_random=False,
                         read_percentage=0,
                         io_count=lba_count//io_size).start().close()
        write_duration = time.time()-write_start
        logging.info("full drive write %d seconds" % write_duration)
        assert write_duration < 1800

        # power cycle
        subsystem.power_cycle(15)
        nvme0.reset()
        
        # read part of drive
        read_time = 1800-write_duration
        nvme0n1.ioworker(io_size=io_size,
                         lba_random=False,
                         read_percentage=100,
                         time=read_time,
                         region_end=lba_count//100).start().close()
        logging.info("loop %d finish" % i)
        
        # power cycle
        subsystem.power_cycle(15)
        nvme0.reset()

