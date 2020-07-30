import time
import pytest
import logging

import nvme as d


def test_swl_only(nvme0: d.Controller, nvme0n1: d.Namespace, verify):
    import matplotlib.pyplot as plt
    
    logging.info("format")
    nvme0n1.format(512)

    io_size = 128
    ns_size = nvme0n1.id_data(7, 0)
    io_count = ns_size//io_size
    logging.info("fill whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=0).start().close()
    
    io_per_second = []
    logging.info("write hot sequential data")
    # 10GB seq write
    nvme0n1.ioworker(io_size=8,
                     lba_random=False,
                     region_end=10*1024*1024*1024//512, #10GB
                     read_percentage=0,
                     time=10*3600,
                     output_io_per_second=io_per_second).start().close()
    logging.info(io_per_second)

    logging.info("verify whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=100).start().close()

    plt.plot(io_per_second)
    plt.ylim(bottom=0)
    plt.xlim(left=0)
    plt.show()
    

def test_swl_with_gc(nvme0: d.Controller, nvme0n1: d.Namespace, verify):
    import matplotlib.pyplot as plt
    
    logging.info("format")
    nvme0n1.format(512)

    io_size = 128
    ns_size = nvme0n1.id_data(7, 0)
    io_count = ns_size//io_size
    logging.info("fill whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=0).start().close()
    
    distribution = [0]*100
    for i in [0, 3, 11, 28, 60, 71, 73, 88, 92, 98]:
        distribution[i] = 1000
    io_per_second = []
    logging.info("write hot random data")
    r = nvme0n1.ioworker(io_size=8,
                     lba_random=True,
                     distribution = distribution,
                     read_percentage=0,
                     time=10*3600,
                     output_io_per_second=io_per_second).start().close()
    logging.info(io_per_second)
    logging.info(r)

    logging.info("verify whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=100).start().close()

    plt.plot(io_per_second)
    plt.ylim(bottom=0)
    plt.show()
    
