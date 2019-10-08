import pytest
import nvme as d

import time
import logging


TEST_SCALE = 10    #1, 10


# trim
@pytest.mark.parametrize("repeat", range(TEST_SCALE))
@pytest.mark.parametrize("lba_count", [8, 8*1024, 0])  # 4K, 4M, all 
def test_trim_time_one_range(nvme0, nvme0n1, lba_count, repeat):
    q = d.Qpair(nvme0, 8)
    buf = d.Buffer(4096)
    if lba_count == 0:
        lba_count = nvme0n1.id_data(7, 0)  # all lba
    buf.set_dsm_range(0, 0, lba_count)
    
    start_time = time.time()
    nvme0n1.dsm(q, buf, 1).waitdone()
    with open("report.csv", "a") as f:
        f.write('%d\n' % (time.time()-start_time))


@pytest.mark.parametrize("repeat", range(TEST_SCALE))
@pytest.mark.parametrize("io_size", [1, 8, 64, 512, 4096])  # 4K, 4M, all 
def test_trim_time_all_range_buffer(nvme0, nvme0n1, repeat, io_size):
    q = d.Qpair(nvme0, 8)
    buf = d.Buffer(4096)
    for i in range(4096//16):
        buf.set_dsm_range(i, i*io_size, io_size)
    
    start_time = time.time()
    nvme0n1.dsm(q, buf, 1).waitdone()
    with open("report.csv", "a") as f:
        f.write('%d\n' % (time.time()-start_time))

    
# format
@pytest.mark.parametrize("repeat", range(TEST_SCALE))
def test_format_time(nvme0n1, repeat):
    start_time = time.time()
    nvme0n1.format()
    with open("report.csv", "a") as f:
        f.write('%d\n' % (time.time()-start_time))
