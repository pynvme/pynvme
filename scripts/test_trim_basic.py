import time
import pytest
import logging
import nvme as d


def test_trim_basic(nvme0, nvme0n1, verify):
    GB = 1024*1024*1024
    databuf = d.Buffer(512)
    trimbuf = d.Buffer(4096)
    q = d.Qpair(nvme0, 32)

    # DUT info
    logging.info("model number: %s" % nvme0.id_data(63, 24, str))
    logging.info("firmware revision: %s" % nvme0.id_data(71, 64, str))

    logging.info("format disk, LBA size is 512 byte");
    nvme0.format(nvme0n1.get_lba_format(512, 0)).waitdone()

    logging.info("write data in 10G ~ 20G")
    io_size = 128*1024//512
    start_lba = 10*GB//512
    lba_count = 10*GB//512
    nvme0n1.ioworker(io_size = io_size,
                     lba_align = io_size,
                     lba_random = False, 
                     read_percentage = 0, 
                     lba_start = start_lba,
                     io_count = lba_count//io_size,
                     qdepth = 128).start().close()

    # verify
    nvme0n1.read(q, databuf, start_lba).waitdone()
    databuf.dump()
    
    # trim
    logging.info("trim the 10G data from LBA %d" % start_lba)
    trimbuf.set_dsm_range(0, start_lba, lba_count)
    trim_cmd = nvme0n1.dsm(q, trimbuf, 1)
    start_time = time.time()
    trim_cmd.waitdone()
    trim_time = time.time()-start_time
    logging.info("trim speed: %dGB/s" % (10/trim_time))

    # verify
    nvme0n1.read(q, databuf, start_lba).waitdone()
    databuf.dump()

    time.sleep(2)

