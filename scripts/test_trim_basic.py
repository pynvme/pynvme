import time
import pytest
import logging
import nvme as d


def test_trim_basic(nvme0, nvme0n1, verify):
    GB = 1024*1024*1024
    databuf = d.Buffer(512)  # all-0 buffer
    trimbuf = d.Buffer(4096)
    q = d.Qpair(nvme0, 32)

    # DUT info
    logging.info("model number: %s" % nvme0.id_data(63, 24, str))
    logging.info("firmware revision: %s" % nvme0.id_data(71, 64, str))

    # format
    lbaf = nvme0n1.get_lba_format(512, 0)
    logging.info("format disk, LBA size is 512 byte, lbaf: %d" % lbaf);
    nvme0.format(lbaf).waitdone()

    # verify data after format
    nvme0n1.compare(q, databuf, 0).waitdone()

    # write
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

    # verify data after write, data should be modified
    with pytest.warns(UserWarning, match="ERROR status: 02/85"):
        nvme0n1.compare(q, databuf, start_lba).waitdone()
    
    # trim
    logging.info("trim the 10G data from LBA %d" % start_lba)
    trimbuf.set_dsm_range(0, start_lba, lba_count)
    trim_cmd = nvme0n1.dsm(q, trimbuf, 1).waitdone()
    #logging.info("trim speed: %dGB/s" % (10/trim_time))

    # verify after trim
    nvme0n1.compare(q, databuf, start_lba).waitdone()

