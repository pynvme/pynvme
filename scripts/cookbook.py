import time
import pytest  #L2
import logging

import nvme as d  #L5


def test_sanitize_operations_basic(nvme0, nvme0n1):  #L8
    if nvme0.id_data(331, 328) == 0:  #L9
        pytest.skip("sanitize operation is not supported")  #L10

    logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))
    nvme0.sanitize().waitdone()  #L13

    # check sanitize status in log page
    buf = d.Buffer(4096)  #L16
    with pytest.warns(UserWarning, match="AER notification is triggered"):
        nvme0.getlogpage(0x81, buf, 20).waitdone()  #L17
        while buf.data(3, 2) & 0x7 != 1:  #L18
            time.sleep(1)
            nvme0.getlogpage(0x81, buf, 20).waitdone()  #L20
            progress = buf.data(1, 0)*100//0xffff
            logging.info("%d%%" % progress)


def test_buffer_read_write(nvme0, nvme0n1):
    buf = d.Buffer(512, 'ascii table')  #L2
    logging.info("physical address of buffer: 0x%lx" % buf.phys_addr)  #L3
    
    for i in range(512):
        buf[i] = i%256  #L6
    print(buf.dump(128))  #L7
    
    buf = d.Buffer(512, 'random', pvalue=100, ptype=0xbeef)  #L15
    print(buf.dump())
    buf = d.Buffer(512, 'random', pvalue=100, ptype=0xbeef)  #L17
    print(buf.dump())

    qpair = d.Qpair(nvme0, 10)
    nvme0n1.write(qpair, buf, 0).waitdone()
    nvme0n1.read(qpair, buf, 0).waitdone()
    print(buf.dump())


def test_create_qpairs(nvme0, nvme0n1, buf):
    qpair = d.Qpair(nvme0, 1024)
    nvme0n1.read(qpair, buf, 0)
    qpair.waitdone()
    nvme0n1.read(qpair, buf, 0, 8).waitdone()
    
    ql = []
    for i in range(15):
        ql.append(d.Qpair(nvme0, 8))

    with pytest.raises(d.QpairCreationError):
        ql.append(d.Qpair(nvme0, 8))

    nvme0n1.ioworker(io_size=8, time=1000).start().close()
        
    del qpair
    nvme0n1.ioworker(io_size=8, time=1).start().close()


def test_namespace_multiple(buf):
    # create all controllers and namespace
    addr_list = [b'3d:00.0']
    nvme_list = [d.Controller(a) for a in addr_list]

    for nvmex in nvme_list:
        qpair = d.Qpair(nvmex, 8)
        nvmexn1 = d.Namespace(nvmex)

        #Check if support write uncorrectable command
        wuecc_support = nvmex.id_data(521, 520) & 0x2
        if wuecc_support != 0:
            nvmexn1.write_uncorrectable(qpair, 0, 8).waitdone()
            with pytest.warns(UserWarning, match="ERROR status: 02/81"):
                nvmexn1.read(qpair, buf, 0, 8).waitdone()
                
            nvmexn1.write(qpair, buf, 0, 8).waitdone()
            def this_read_cb(dword0, status1):
                assert status1>>1 == 0
                nvmexn1.write_uncorrectable(qpair, 0, 8)
            nvmexn1.read(qpair, buf, 0, 8, cb=this_read_cb).waitdone(2)

            def another_read_cb(dword0, status1):
                logging.info("dword0: 0x%08x" % dword0)
                logging.info("phase bit: %d" % (status1&1))
                logging.info("dnr: %d" % ((status1>>15)&1))
                logging.info("more: %d" % ((status1>>14)&1))
                logging.info("sct: 0x%x" % ((status1>>9)&0x7))
                logging.info("sc: 0x%x" % ((status1>>1)&0xff))
            with pytest.warns(UserWarning, match="ERROR status: 02/81"):
                nvmexn1.read(qpair, buf, 0, 8, cb=another_read_cb).waitdone()

                
def test_power_and_reset(nvme0, nvme0n1, subsystem, pcie):
    pcie.aspm = 2              # ASPM L1
    pcie.power_state = 3       # PCI PM D3hot
    pcie.aspm = 0
    pcie.power_state = 0
    
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    pcie.reset()               # PCIe reset: hot reset, TS1, TS2
    nvme0.reset()              # reset controller after pcie reset
    nvme0.getfeatures(7).waitdone()

    subsystem.reset()          # NVMe subsystem reset: NSSR
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()

    subsystem.power_cycle(10)  # power cycle NVMe device: cold reset
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()            

    with nvme0n1.ioworker(io_size=8, time=100), \
         nvme0n1.ioworker(io_size=8, time=100), \
         nvme0n1.ioworker(io_size=8, time=100):
        time.sleep(5)
        subsystem.power_cycle(10)
        nvme0.reset()
    nvme0.getfeatures(7).waitdone()            
    
            
@pytest.mark.parametrize("qcount", [1, 1, 2, 4])
def test_ioworker_iops_multiple_queue(nvme0n1, qcount):
    l = []
    io_total = 0
    for i in range(qcount):
        a = nvme0n1.ioworker(io_size=8, lba_align=8,
                             region_start=0, region_end=256*1024*8, # 1GB space
                             lba_random=False, qdepth=16,
                             read_percentage=100, time=10).start()
        l.append(a)

    for a in l:
        r = a.close()
        io_total += r.io_count_read

    logging.info("Q %d IOPS: %.3fK" % (qcount, io_total/10000))


@pytest.mark.parametrize("iops", [100, 10*1000, 1000*1000])
def test_ioworker_fixed_iops(nvme0n1, iops):
    output_io_per_second = []
    nvme0n1.ioworker(io_size=8,
                     lba_random=True,
                     read_percentage=100,
                     iops=iops,
                     output_io_per_second=output_io_per_second, 
                     time=10).start().close()
    logging.info(output_io_per_second)
    

def test_dsm_trim(nvme0: d.Controller, nvme0n1: d.Namespace):
    trimbuf = d.Buffer(4096)
    q = d.Qpair(nvme0, 32)

    # DUT info
    logging.info("model number: %s" % nvme0.id_data(63, 24, str))
    logging.info("firmware revision: %s" % nvme0.id_data(71, 64, str))

    # single range
    start_lba = 0
    lba_count = 8*1024
    trimbuf.set_dsm_range(0, start_lba, lba_count)
    nvme0n1.dsm(q, trimbuf, 1, attribute=0x4).waitdone()

    # multiple range
    lba_count = lba_count//256
    for i in range(256):
        trimbuf.set_dsm_range(i, start_lba+i*lba_count, lba_count)
    nvme0n1.dsm(q, trimbuf, 256).waitdone()


def test_ioworker_performance(nvme0n1):
    import matplotlib.pyplot as plt

    output_io_per_second = []
    percentile_latency = dict.fromkeys([90, 99, 99.9, 99.99, 99.999])
    nvme0n1.ioworker(io_size=8,
                     lba_random=True,
                     read_percentage=100,
                     output_io_per_second=output_io_per_second,
                     output_percentile_latency=percentile_latency, 
                     time=10).start().close()
    logging.info(output_io_per_second)
    logging.info(percentile_latency)

    X = []
    Y = []
    for _, k in enumerate(percentile_latency):
        X.append(k)
        Y.append(percentile_latency[k])

    plt.plot(X, Y)
    plt.xscale('log')
    plt.yscale('log')
    #plt.show()


def test_ioworker_jedec_enterprise_workload(nvme0n1):
    distribution = [1000]*5 + [200]*15 + [25]*80
    iosz_distribution = {1: 4,
                         2: 1,
                         3: 1,
                         4: 1,
                         5: 1,
                         6: 1,
                         7: 1,
                         8: 67,
                         16: 10,
                         32: 7,
                         64: 3,
                         128: 3}

    nvme0n1.ioworker(io_size=iosz_distribution,
                     distribution = distribution,
                     lba_random=True,
                     read_percentage=0,
                     ptype=0xbeef, pvalue=100, 
                     time=10).start().close()    


from psd import IOCQ, IOSQ, PRP, PRPList, SQE, CQE
def test_send_cmd_2sq_1cq(nvme0):
    cq = IOCQ(nvme0, 1, 10, PRP())
    sq1 = IOSQ(nvme0, 1, 10, PRP(), cqid=1)
    sq2 = IOSQ(nvme0, 2, 16, PRP(), cqid=1)

    cdw = SQE(8, 0, 0)
    cdw.nsid = 1  # namespace id
    cdw.cid = 222
    sq1[0] = cdw

    sqe = SQE(*cdw)
    assert sqe[1] == 1
    sqe.cid = 111
    sq2[0] = sqe
    sq2.tail = 1
    time.sleep(0.1)
    sq1.tail = 1
    time.sleep(0.1)
    
    cqe = CQE(cq[0])
    assert cqe.sct == 0
    assert cqe.sc == 0
    assert cqe.sqid == 2
    assert cqe.sqhd == 1
    assert cqe.p == 1
    assert cqe.cid == 111
    
    cqe = CQE(cq[1])
    assert cqe.sct == 0
    assert cqe.sc == 0
    assert cqe.sqid == 1
    assert cqe.sqhd == 1
    assert cqe.p == 1
    assert cqe.cid == 222

    cq.head = 2

    sq1.delete()
    sq2.delete()
    cq.delete()


def subprocess_trim(pciaddr, seconds):
    nvme0 = d.Controller(pciaddr, True)
    nvme0n1 = d.Namespace(nvme0)
    q = d.Qpair(nvme0, 8)
    buf = d.Buffer(4096)
    buf.set_dsm_range(0, 8, 8)

    # send trim commands
    start = time.time()
    while time.time()-start < seconds:
        nvme0n1.dsm(q, buf, 1).waitdone()
    
def test_ioworker_with_temperature_and_trim(nvme0, nvme0n1):
    test_seconds = 10
    
    # start trim process
    import multiprocessing
    mp = multiprocessing.get_context("spawn")
    p = mp.Process(target = subprocess_trim,
                   args = (nvme0.addr, test_seconds))
    p.start()

    # start read/write ioworker and admin commands
    smart_log = d.Buffer(512, "smart log")
    with nvme0n1.ioworker(io_size=256,
                          lba_random=False, 
                          read_percentage=0, 
                          time=test_seconds):
        for i in range(15):
            time.sleep(1)
            nvme0.getlogpage(0x02, smart_log, 512).waitdone()
            ktemp = smart_log.data(2, 1)
            
            from pytemperature import k2c
            logging.info("temperature: %0.2f degreeC" % k2c(ktemp))

    # wait trim process complete
    p.join()


def test_multiple_controllers_and_namespaces():
    # address list of the devices to test
    addr_list = [b'01:00.0', b'02:00.0', b'03:00.0', b'04:00.0']  #L3
    addr_list = [b'3d:00.0']  #L3
    test_seconds = 10

    # create all controllers and namespace
    nvme_list = [d.Controller(a) for a in addr_list]  #L7
    ns_list = [d.Namespace(n) for n in nvme_list]  #L8

    # create two ioworkers on each namespace
    ioworkers = []
    for ns in ns_list:  #L12
        w = ns.ioworker(io_size=8, lba_align=8,
                        region_start=0, region_end=256*1024*8, # 1GB space
                        lba_random=False, qdepth=64,
                        read_percentage=100, time=test_seconds).start()
        ioworkers.append(w)
        w = ns.ioworker(io_size=8, lba_align=16,
                        region_start=256*1024*8, region_end=2*256*1024*8,
                        lba_random=True, qdepth=256,
                        read_percentage=0, time=test_seconds).start()
        ioworkers.append(w)
        
    # collect test results
    io_total = 0
    for w in ioworkers:  #L26
        r = w.close()
        io_total += (r.io_count_read+r.io_count_nonread)
    logging.info("total throughput: %d IOPS" % (io_total/test_seconds))  #L29
    
    
def test_static_wear_leveling(nvme0: d.Controller, nvme0n1: d.Namespace, verify):
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
    logging.info("write hot data")
    nvme0n1.ioworker(io_size=8,
                     lba_random=True,
                     distribution = distribution,
                     read_percentage=0,
                     time=10*3600,
                     output_io_per_second=io_per_second).start().close()
    logging.info(io_per_second)

    logging.info("verify whole drive")
    nvme0n1.ioworker(io_size=io_size,
                     lba_random=False,
                     io_count=io_count,
                     read_percentage=100).start().close()    
        

def test_power_on_off(nvme0):
    def poweron():
        logging.info("poweron")
        pass
    def poweroff():
        logging.info("poweroff")
        pass
    subsystem = d.Subsystem(nvme0, poweron, poweroff)
    
    subsystem = d.Subsystem(nvme0)
    subsystem.poweroff()
    subsystem.poweron()
    nvme0.reset()

    
def test_init_nvme_customerized(pciaddr):
    pcie = d.Pcie(pciaddr)
    nvme0 = d.Controller(pcie, skip_nvme_init=True)
    
    # 1. set pcie registers
    pcie.aspm = 0

    # 2. disable cc.en and wait csts.rdy to 0
    nvme0[0x14] = 0
    while not (nvme0[0x1c]&0x1) == 0: pass

    # 3. set admin queue registers
    nvme0.init_adminq()

    # 4. set register cc
    nvme0[0x14] = 0x00460000

    # 5. enable cc.en
    nvme0[0x14] = 0x00460001

    # 6. wait csts.rdy to 1
    while not (nvme0[0x1c]&0x1) == 1: pass

    # 7. identify controller
    nvme0.identify(d.Buffer(4096)).waitdone()

    # 8. create and identify all namespace
    nvme0.init_ns()

    # 9. set/get num of queues
    nvme0.setfeatures(0x7, cdw11=0x00ff00ff).waitdone()
    nvme0.getfeatures(0x7).waitdone()

    
def test_ioworker_op_dict_trim(nvme0n1):
    cmdlog_list = [None]*10000
    op_percentage = {2: 40, 9: 30, 1: 30}
    nvme0n1.ioworker(io_size=8,
                     io_count=10000,
                     op_percentage=op_percentage,
                     output_cmdlog_list=cmdlog_list).start().close()
    
    op_log = [c[2] for c in cmdlog_list]
    for op in (2, 9, 1):
        logging.info("occurance of %d: %d" % (op, op_log.count(op)))


def test_ioworker_io_sequence_read_write_trim_flush_uncorr(nvme0n1):
    cmd_seq = [(000000, 1, 0, 8),  #L2
               (200000, 2, 3, 1),
               (400000, 1, 2, 1),
               (600000, 9, 1, 1),
               (800000, 4, 0, 8),
               (1000000, 0, 0, 0)]
    cmdlog_list = [None]*len(cmd_seq)  #L8

    r = nvme0n1.ioworker(io_sequence=cmd_seq,  #L10
                         output_cmdlog_list=cmdlog_list).start().close()

    assert r.mseconds > 1000  #L13
    assert cmdlog_list[-1][2] == 0  #L14
    assert cmdlog_list[-2][2] == 4
    assert cmdlog_list[-3][2] == 9
    assert cmdlog_list[-4][2] == 1
    assert cmdlog_list[-5][2] == 2
    assert cmdlog_list[-6][2] == 1


def test_aer_with_multiple_sanitize(nvme0, nvme0n1, buf):  #L8
    if nvme0.id_data(331, 328) == 0:  #L9
        pytest.skip("sanitize operation is not supported")  #L10

    logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))

    for i in range(3):
        nvme0.sanitize().waitdone()  #L13

        # check sanitize status in log page
        with pytest.warns(UserWarning, match="AER notification is triggered"):
            nvme0.getlogpage(0x81, buf, 20).waitdone()  #L17
            while buf.data(3, 2) & 0x7 != 1:  #L18
                time.sleep(1)
                nvme0.getlogpage(0x81, buf, 20).waitdone()  #L20
                progress = buf.data(1, 0)*100//0xffff
                logging.info("%d%%" % progress)
                
        nvme0.waitdone()
        nvme0.aer()


def test_read_write_mixed_verify(nvme0n1, verify):  #L1
    with nvme0n1.ioworker(io_size=8, lba_align=8,
                          region_start=0, region_end=256,
                          lba_random=True, qdepth=64,
                          read_percentage=0, time=1):  #L5
        pass
    with nvme0n1.ioworker(io_size=8, lba_align=8,
                          region_start=0, region_end=256,
                          lba_random=True, qdepth=64,
                          read_percentage=100, time=1):  #L10
        pass
    
    with pytest.warns(UserWarning, match="ERROR status: 02/81"):  #L13
        with nvme0n1.ioworker(io_size=8, lba_align=8,
                              region_start=0, region_end=256,
                              lba_random=True, qdepth=64,
                              read_percentage=0, time=1), \
             nvme0n1.ioworker(io_size=8, lba_align=8,
                              region_start=0, region_end=256,
                              lba_random=True, qdepth=64,
                              read_percentage=100, time=1):  #L21
            pass        


def test_verify_partial_namespace(nvme0):
    region_end=1024*1024*1024//512  # 1GB space
    nvme0n1 = d.Namespace(nvme0, 1, region_end)
    assert True == nvme0n1.verify_enable(True)

    nvme0n1.ioworker(io_size=8,
                     lba_random=True,
                     region_end=region_end,
                     read_percentage=50,
                     time=30).start().close()
    

def test_jsonrpc_list_qpairs(pciaddr):
    import json
    import socket

    # create the jsonrpc client
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect('/var/tmp/pynvme.sock')

    def jsonrpc_call(sock, method, params=[]):
        # create and send the command
        req = {}
        req['id'] = 1234567890
        req['jsonrpc'] = '2.0'
        req['method'] = method
        req['params'] = params
        sock.sendall(json.dumps(req).encode('ascii'))

        # receive the result
        resp = json.loads(sock.recv(4096).decode('ascii'))
        assert resp['id'] == 1234567890
        assert resp['jsonrpc'] == '2.0'
        return resp['result']

    # create controller and admin queue
    nvme0 = d.Controller(d.Pcie(pciaddr))
    
    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 1
    assert result[0]['qid']-1 == 0
    
    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 1
    assert result[0]['qid']-1 == 0

    q1 = d.Qpair(nvme0, 8)
    result = jsonrpc_call(sock, 'list_all_qpair')
    assert len(result) == 2
    assert result[0]['qid']-1 == 0
    assert result[1]['qid']-1 == 1

    q2 = d.Qpair(nvme0, 8)        
