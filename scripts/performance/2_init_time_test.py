import pytest
import nvme as d

import time
import logging


TEST_SCALE = 10  #10, 1


def do_power_cycle(dirty, subsystem, nvme0n1, nvme0):
    if not dirty:
        # notify drive for a clean shutdown
        start_time = time.time()
        subsystem.shutdown_notify()
        logging.info("notify time %.6f sec" % (time.time()-start_time))

    # boot again
    csv_start = time.time()
    start_time = time.time()
    subsystem.power_cycle(10)
    nvme0.reset()
    logging.info("init time %.6f sec" % (time.time()-start_time-10))

    # first read time
    start_time = time.time()
    q = d.Qpair(nvme0, 16)
    b = d.Buffer(512)
    lba = nvme0n1.id_data(7, 0) - 1
    nvme0n1.read(q, b, lba).waitdone()
    logging.info("media ready time %.6f sec" % (time.time()-start_time))
    q.delete()
    
    # report to csv
    ready_time = time.time()-csv_start-10
    with open("report.csv", "a") as f:
        f.write('%.6f\n' % ready_time)

    
# rand write clean boot time
@pytest.mark.parametrize("repeat", range(TEST_SCALE))
@pytest.mark.parametrize("dirty", [False, True])
def test_boot_time_rand(nvme0, nvme0n1, subsystem, repeat, dirty):
    # write to make drive dirty
    with nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=True, qdepth=64,
                          read_percentage=0, time=TEST_SCALE):
        pass

    do_power_cycle(dirty, subsystem, nvme0n1, nvme0)

    
# seq write clean boot time
@pytest.mark.parametrize("repeat", range(TEST_SCALE))
@pytest.mark.parametrize("dirty", [False, True])
def test_boot_time_seq(nvme0, nvme0n1, subsystem, repeat, dirty):
    # write to make drive dirty
    with nvme0n1.ioworker(io_size=128, lba_align=128,
                          lba_random=False, qdepth=64,
                          read_percentage=0, time=TEST_SCALE):
        pass
    
    do_power_cycle(dirty, subsystem, nvme0n1, nvme0)
