import pytest
import nvme as d

import time
import logging


rand = True
seq = False


def do_fill_drive(rand, nvme0n1, region_end):
    io_size = 8 if rand else 128
    ns_size = nvme0n1.id_data(7, 0)
    io_count = ns_size//io_size
    io_per_second = []
    
    nvme0n1.ioworker(io_size=io_size, lba_align=io_size,
                     lba_random=rand, qdepth=512,
                     region_end=region_end,
                     io_count=io_count, read_percentage=0,
                     output_io_per_second=io_per_second).start().close()
    logging.info(io_per_second)

    
# full drive seq write
def test_clean_and_fill_drive(nvme0n1):
    nvme0n1.format(512)
    do_fill_drive(seq, nvme0n1, nvme0n1.id_data(7, 0))


# random write 20% region to steady
def test_random_write_small_region(nvme0n1):
    do_fill_drive(rand, nvme0n1, nvme0n1.id_data(7, 0)//5)

    
# iops: read/write/mixed
# latency: read/write/mixed
@pytest.mark.parametrize("readp", [100, 0, 67])
def test_steady_iops_latency(nvme0n1, readp):
    percentile_latency = dict.fromkeys([50, 90, 99, 99.9, 99.999])
    io_per_second = []

    w = nvme0n1.ioworker(io_size=8, lba_align=8,
                         lba_random=rand, qdepth=64,
                         region_end=nvme0n1.id_data(7, 0)//5, 
                         time=1000, read_percentage=readp,
                         output_percentile_latency=percentile_latency, 
                         output_io_per_second=io_per_second).start()
    w.close()
    logging.info(io_per_second)
    logging.info(w.iops_consistency(90))
    logging.info(percentile_latency)

    # latency against iops
    # r.latency_average_us
