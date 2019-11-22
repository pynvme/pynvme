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


from psd import IOCQ, IOSQ, PRP, PRPList, SQE, CQE

def test_send_cmd_2sq_1cq(nvme0):
    # 2 SQ share one CQ
    cq = IOCQ(nvme0, 1, 10, PRP())
    sq1 = IOSQ(nvme0, 1, 10, PRP(), cqid=1)
    sq2 = IOSQ(nvme0, 2, 16, PRP(), cqid=1)

    # write lba0, 16K data organized by PRPList
    write_cmd = SQE(1, 1)  # write to namespace 1
    write_cmd.prp1 = PRP() # PRP1 is a 4K page
    prp_list = PRPList()   # PRPList contains 3 pages
    prp_list[0] = PRP()
    prp_list[1] = PRP()
    prp_list[2] = PRP()
    write_cmd.prp2 = prp_list   # PRP2 points to the PRPList
    write_cmd[10] = 0           # starting LBA
    write_cmd[12] = 31          # LBA count: 32, 16K, 4 pages
    write_cmd.cid = 123;        # verify cid later

    # send write commands in both SQ
    sq1[0] = write_cmd          # fill command dwords in SQ1
    write_cmd.cid = 567;        # verify cid later
    sq2[0] = write_cmd          # fill command dwords in SQ2
    sq2.tail = 1                # ring doorbell of SQ2 first
    time.sleep(0.1)             # delay to ring SQ1, 
    sq1.tail = 1                #  so command in SQ2 should comple first

    # wait for 2 command completions
    while CQE(cq[1]).p == 0: pass

    # check first cpl
    cqe = CQE(cq[0])
    assert cqe.sqid == 2
    assert cqe.sqhd == 1
    assert cqe.cid == 567

    # check second cpl
    cqe = CQE(cq[1])
    assert cqe.sqid == 1
    assert cqe.sqhd == 1
    assert cqe.cid == 123

    # update cq head doorbell to device
    cq.head = 2

    # delete all queues
    sq1.delete()
    sq2.delete()
    cq.delete()
