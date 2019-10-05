import pytest
import nvme as d

import logging


rand = True
seq = False

read = True
write = False

def do_ioworker(rand, read, ns):
    """ run ioworkers for basic io performance tests"""
    
    seconds = 10
    io_size = 8 if rand else 128 # 4K or 64K
    rp = 100 if read else 0 # read or write
    
    r = ns.ioworker(io_size=io_size, lba_align=io_size,
                    region_start=0, region_end=256*1024*8, # 1GB space
                    lba_random=rand, qdepth=512,
                    read_percentage=rp, time=seconds).start().close()

    io_total = r.io_count_read+r.io_count_write
    iops = io_total//seconds

    return iops if rand else iops*io_size*512  # return Bps for seq IO


def do_fill_drive(rand, nvme0n1):
    io_size = 8 if rand else 128
    ns_size = nvme0n1.id_data(7, 0)
    io_count = ns_size//io_size
    io_per_second = []
    
    r = nvme0n1.ioworker(io_size=io_size, lba_align=io_size,
                         lba_random=rand, qdepth=512,
                         io_count=io_count, read_percentage=0,
                         output_io_per_second=io_per_second).start().close()
    logging.info(io_per_second)


# empty read
def test_empty_read_performance(nvme0n1):
    nvme0n1.format(512)  # 512 sector size
    logging.info(do_ioworker(seq, read, nvme0n1))
    logging.info(do_ioworker(rand, read, nvme0n1))

    
# write/read 128K in 1GB, cdm
def test_1gb_read_write_performance(nvme0n1):
    logging.info(do_ioworker(seq, write, nvme0n1))
    logging.info(do_ioworker(rand, write, nvme0n1))
    logging.info(do_ioworker(seq, read, nvme0n1))
    logging.info(do_ioworker(rand, read, nvme0n1))


# full drive seq write
def test_fill_drive_first_pass(nvme0n1):
    do_fill_drive(seq, nvme0n1)

    
# random
@pytest.mark.parametrize("repeat", range(2))
def test_fill_drive_randome(nvme0n1, repeat):
    do_fill_drive(rand, nvme0n1)


# 2-pass full drive seq write
@pytest.mark.parametrize("repeat", range(2))
def test_fill_drive_after_random(nvme0n1, repeat):
    do_fill_drive(seq, nvme0n1)

    
