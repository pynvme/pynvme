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
                             read_percentage=100, time=50*3600).start()
        l.append(a)

    for a in l:
        r = a.close()
        io_total += (r.io_count_read+r.io_count_nonread)

    logging.info("Q %d IOPS: %.3fK" % (qcount, io_total/50000/3600))

    
def test_write_and_read_to_eol(nvme0, subsystem, nvme0n1: d.Namespace, verify):
    assert verify
    
    # format drive
    nvme0n1.format()
    lba_count = nvme0n1.id_data(7, 0)

    # test for PE cycles
    for i in range(TEST_LOOPS):
        logging.info(f"loop {i} start")

        # write 1 pass of whole drive
        io_size = 64*1024//512  # 64KB
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


def test_read_multiple_devices_50hr(verify):
    assert verify

    # address list of the devices to test
    addr_list = [b'71:00.0', b'72:00.0', b'02:00.0', b'03:00.0']
    test_seconds = 50*3600
    
    nvme_list = [d.Controller(a) for a in addr_list]
    ns_list = [d.Namespace(n) for n in nvme_list]

    # operations on multiple controllers
    for nvme in nvme_list:
        logging.info("device: %s" % nvme.id_data(63, 24, str))

    logging.info("sequential write to fill the whole namespace")
    ioworkers = {}
    for ns in ns_list:
        lba_max = ns.id_data(7, 0)
        io_size = 128 # 64K
        a = ns.ioworker(io_size=io_size, lba_random=False, qdepth=16,
                        read_percentage=0, io_count=lba_max//io_size).start()
        ioworkers[ns] = a

    # wait for all ioworker done
    [ioworkers[ns].close() for ns in ioworkers]

    logging.info("4K read for 500hr") 
    ioworkers = {}
    for ns in ns_list:
        a = ns.ioworker(io_size=8, lba_random=True, qdepth=16,
                        read_percentage=100, time=test_seconds).start()
        ioworkers[ns] = a

    # display progress
    for i in range(test_seconds):
        time.sleep(1)
        buf = d.Buffer(512)
        for nvme in nvme_list:
            nvme.getlogpage(2, buf).waitdone()
            logging.info("%9d: %s data units read %d" %
                         (i, nvme.id_data(63, 24, str), buf.data(47, 32)))
        
    # wait for all ioworker done
    [ioworkers[ns].close() for ns in ioworkers]
