import pytest
import nvme as d

import time
import logging


rand = True
seq = False


def do_enterprise_endurance_workload(nvme0n1, iops_scale=100, tsc=10):
    bandwidth = 0
    distribution = [1000]*5 + [200]*15 + [25]*80
    iops_distribution = {1: 4,
                         2: 1,
                         3: 1,
                         4: 5,
                         5: 1,
                         6: 1,
                         7: 1,
                         8: 67,
                         16: 10,
                         32: 7,
                         64: 3,
                         128: 3}

    # start ioworker for different IO size
    for lba_size in iops_distribution:
        iops = iops_distribution[lba_size] * iops_scale
        logging.debug(iops)
        a = nvme0n1.ioworker(io_size=lba_size,
                             lba_align=min(lba_size, 8),
                             lba_random=True,
                             qdepth=32,
                             iops=iops, 
                             distribution = distribution,
                             read_percentage=0,
                             time=tsc).start()
        iops_distribution[lba_size] = a

    # return the total bandwidth
    for lba_size in iops_distribution:
        a = iops_distribution[lba_size]
        r = a.close()
        logging.debug(r.io_count_read+r.io_count_write)
        bandwidth += (r.io_count_read+r.io_count_write)*lba_size
    return bandwidth*512/tsc


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

    
def test_precondition(nvme0n1):
    # clear and fill drive
    nvme0n1.format(512)
    do_fill_drive(seq, nvme0n1, nvme0n1.id_data(7, 0))

    # randome write to steady
    do_fill_drive(rand, nvme0n1, nvme0n1.id_data(7, 0))

    
def test_jesd219a_enterprise_endurance_workload(nvme0n1):
    # find the largest iops scale to the test
    max_scale = 0
    base = do_enterprise_endurance_workload(nvme0n1, 50)
    for i in range(2, 20):
        scale = i*50
        bw = do_enterprise_endurance_workload(nvme0n1, scale)
        if bw/(base*i) < 0.9:
            max_scale = scale-50
            break

    # long time endurance test at largest possible bandwidth
    logging.info("max iops scale: %d" % max_scale)
    assert max_scale != 0
    tsc = 3600
    tbw_total = 0
    for i in range(1, 1000):
        bw = do_enterprise_endurance_workload(nvme0n1, max_scale, 3600)
        tbw = bw*3600
        tbw_total += tbw
        logging.info("%5d hours, TBW: %d" % (i, tbw_total))
