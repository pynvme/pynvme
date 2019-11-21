import time
import pytest
import logging
import nvme as d

def test_hello_world(nvme0, nvme0n1: d.Namespace):
    read_buf = d.Buffer(512)
    data_buf = d.Buffer(512)
    data_buf[10:21] = b'hello world'
    qpair = d.Qpair(nvme0, 16)  # create IO SQ/CQ pair, with 16 queue-depth
    assert read_buf[10:21] != b'hello world'

    def write_cb(cdw0, status1):  # command callback function
        nvme0n1.read(qpair, read_buf, 0, 1)
    nvme0n1.write(qpair, data_buf, 0, 1, cb=write_cb)
    qpair.waitdone(2)
    assert read_buf[10:21] == b'hello world'

    
from pytemperature import k2c

def test_ioworker_with_temperature(nvme0, nvme0n1):
    smart_log = d.Buffer(512, "smart log")
    with nvme0n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=30):
        for i in range(40):
            nvme0.getlogpage(0x02, smart_log, 512).waitdone()
            ktemp = smart_log.data(2, 1)
            logging.info("temperature: %0.2f degreeC" % k2c(ktemp))
            time.sleep(1)

            
def test_trim_basic(nvme0: d.Controller, nvme0n1: d.Namespace, verify):
    GB = 1024*1024*1024
    all_zero_databuf = d.Buffer(512)
    trimbuf = d.Buffer(4096)
    q = d.Qpair(nvme0, 32)

    # DUT info
    logging.info("model number: %s" % nvme0.id_data(63, 24, str))
    logging.info("firmware revision: %s" % nvme0.id_data(71, 64, str))

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
        nvme0n1.compare(q, all_zero_databuf, start_lba).waitdone()

    # get the empty trim time
    trimbuf.set_dsm_range(0, 0, 0)
    trim_cmd = nvme0n1.dsm(q, trimbuf, 1).waitdone() # first call is longer, due to cache?
    start_time = time.time()
    trim_cmd = nvme0n1.dsm(q, trimbuf, 1).waitdone()
    empty_trim_time = time.time()-start_time

    # the trim time on device-side only
    logging.info("trim the 10G data from LBA 0x%lx" % start_lba)
    trimbuf.set_dsm_range(0, start_lba, lba_count)
    start_time = time.time()
    trim_cmd = nvme0n1.dsm(q, trimbuf, 1).waitdone()
    trim_time = time.time()-start_time-empty_trim_time
    logging.info("trim bandwidth: %0.2fGB/s" % (10/trim_time))

    # verify after trim
    nvme0n1.compare(q, all_zero_databuf, start_lba).waitdone()


@pytest.mark.parametrize("loading", [0, 100])
def test_aer_smart_temperature(nvme0, loading, aer):
    import time
    start_time = time.time()

    smart_log = d.Buffer(512, "smart log")
    assert smart_log.data(2, 1) == 0

    # aer callback function
    def cb(cdw0, status):
        # set temp threshold back
        logging.info("in aer cb, status 0x%x" % status)
        nvme0.setfeatures(0x04, cdw11=320)
        nvme0.getlogpage(0x02, smart_log, 512)
    aer(cb)

    # overlap the cmdlog
    for i in range(10000):
        nvme0.getfeatures(0x07).waitdone()

    # fill with getfeatures cmd as noise for 10 seconds
    def getfeatures_cb(cdw0, status):
        if smart_log.data(2, 1) < 256 and \
           time.time()-start_time < 10:
            nvme0.getfeatures(0x07, cb=getfeatures_cb)
    for i in range(loading):
        nvme0.getfeatures(0x07, cb=getfeatures_cb)

    # set temp threshold to trigger aer
    nvme0.setfeatures(0x04, cdw11=200)
    with pytest.warns(UserWarning, match="AER notification"):
        while smart_log.data(2, 1) == 0:
            nvme0.waitdone()
    assert smart_log.data(2, 1) != 0
    assert smart_log.data(2, 1) > 256

    logging.info("it should be soon to trigger aer: %ds" %
                 (time.time()-start_time))
    assert time.time()-start_time < 15.0


def test_multiple_controllers_and_namespaces():
    # address list of the devices to test
    addr_list = [b'02:00.0', b'03:00.0', b'71:00.0', b'72:00.0']
    test_seconds = 10
    
    nvme_list = [d.Controller(a) for a in addr_list]
    ns_list = [d.Namespace(n) for n in nvme_list]

    # operations on multiple controllers
    for nvme in nvme_list:
        logging.info("device: %s" % nvme.id_data(63, 24, str))

    # format for faster read
    # for ns in ns_list:
    #     ns.format(512)
        
    # multiple namespaces and ioworkers
    ioworkers = {}
    for ns in ns_list:
        a = ns.ioworker(io_size=256, lba_align=256,
                        region_start=0, region_end=256*1024*8, # 1GB space
                        lba_random=False, qdepth=64,
                        read_percentage=100, time=test_seconds).start()
        ioworkers[ns] = a

    # test results
    io_total = 0
    for ns in ioworkers:
        r = ioworkers[ns].close()
        io_total += (r.io_count_read+r.io_count_write)
    logging.info("total bandwidth: %.3fMB/s" % ((128*io_total)/1000/test_seconds))
    
        
def test_spdk_summit_demo(nvme0, nvme0n1):
    logging.info("writing to PCIe SSD and monitoring the temperature")
    nvmt = d.Controller(b'127.0.0.1:4420')
    with nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=False, qdepth=10,
                          read_percentage=33, time=10), \
         nvme0n1.ioworker(io_size=8, lba_align=8,
                          lba_random=False, qdepth=50,
                          read_percentage=67, time=20):
        # read the SMART temperature
        smart_log = d.Buffer(512, "smart log")
        for i in range(30):
            for n in (nvme0, nvmt):
                n.getlogpage(0x02, smart_log, 512).waitdone()
                ktemp = smart_log.data(2, 1)
                logging.info("temperature %d: %0.2f degreeC" % (i, k2c(ktemp)))
            time.sleep(1)

    test_hello_world(nvmt, d.Namespace(nvmt))
