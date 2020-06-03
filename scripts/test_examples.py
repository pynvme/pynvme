import time
import pytest
import logging

import nvme as d


# intuitive, spec, qpair, vscode, debug, cmdlog, assert
def test_hello_world(nvme0, nvme0n1):
    # prepare data buffer and IO queue
    read_buf = d.Buffer(512)
    write_buf = d.Buffer(512)
    write_buf[10:21] = b'hello world'
    qpair = d.Qpair(nvme0, 16)  # create IO SQ/CQ pair, with 16 queue-depth

    # send write and read command
    def write_cb(cdw0, status1):  # command callback function
        nvme0n1.read(qpair, read_buf, 0, 1)
    nvme0n1.write(qpair, write_buf, 0, 1, cb=write_cb)

    # wait commands complete and verify data
    assert read_buf[10:21] != b'hello world'
    qpair.waitdone(2)
    assert read_buf[10:21] == b'hello world'


# access PCIe/NVMe registers, identify data, pythonic
def test_registers_and_identify_data(pcie, nvme0, nvme0n1):
    logging.info("0x%x, 0x%x" % (pcie[0], pcie.register(0, 2)))
    logging.info("0x%08x, 0x%08x" % (nvme0[0], nvme0[4]))
    logging.info("model name: %s" % nvme0.id_data(63, 24, str))
    logging.info("vid: 0x%x" % nvme0.id_data(1, 0))
    logging.info("namespace size: %d" % nvme0n1.id_data(7, 0))


# Controller, sanitize, default parameters, getlogpage
def test_sanitize(nvme0: d.Controller, buf):
    if nvme0.id_data(331, 328) == 0:
        pytest.skip("sanitize operation is not supported")

    import PySimpleGUI as sg
        
    logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))
    sg.OneLineProgressMeter('sanitize progress', 0, 100, 'progress', orientation='h')
    nvme0n1 = d.Namespace(nvme0, 1, 128*1000*1000//4)
    nvme0.sanitize().waitdone()  # sanitize clears namespace

    # check sanitize status in log page
    nvme0.getlogpage(0x81, buf, 20).waitdone()
    while buf.data(3, 2) & 0x7 != 1:  # sanitize operation is not completed
        time.sleep(1)
        nvme0.getlogpage(0x81, buf, 20).waitdone()
        progress = buf.data(1, 0)*100//0xffff
        sg.OneLineProgressMeter('sanitize progress', progress, 100, 'progress', orientation='h')
        logging.info("%d%%" % progress)


# simple ioworker, complicated io_size, python function call, CI
def test_ioworker_simplified(nvme0, nvme0n1: d.Namespace):
    nvme0n1.ioworker(time=1).start().close()
    nvme0n1.ioworker(io_size=[1, 2, 3, 7, 8, 16], time=1).start().close()
    nvme0n1.ioworker(op_percentage={2:10, 1:20, 0:30, 9:40}, time=1).start().close()
    test_hello_world(nvme0, nvme0n1)

    
# ioworker with admin commands, multiprocessing, log, cmdlog, pythonic
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


# multiple ioworkers, PCIe, TCP, CPU, performance, ioworker return values
def test_multiple_controllers_and_namespaces():
    # address list of the devices to test
    addr_list = ['01:00.0', '03:00.0', '192.168.0.3', '127.0.0.1:4420']
    addr_list = ['3d:00.0']
    test_seconds = 10

    # create all controllers and namespace
    nvme_list = [d.Controller(d.Pcie(a)) for a in addr_list]
    ns_list = [d.Namespace(n) for n in nvme_list]

    # create two ioworkers on each namespace
    ioworkers = []
    for ns in ns_list:
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
    for w in ioworkers:
        r = w.close()
        io_total += (r.io_count_read+r.io_count_nonread)
    logging.info("total throughput: %d IOPS" % (io_total/test_seconds))
    

# GUI, productivity
def test_get_log_page(nvme0):
    import PySimpleGUI as sg
    
    lid = int(sg.PopupGetText("Which Log ID to read?", "pynvme"))
    buf = d.Buffer(512, "%s, Log ID: %d" % (nvme0.id_data(63, 24, str), lid))
    nvme0.getlogpage(lid, buf).waitdone()
    
    layout = [ [sg.OK(), sg.Cancel()],
               [sg.Multiline(buf.dump(), enter_submits=True, disabled=True, size=(80, 25))] ]
    sg.Window(str(buf), layout, font=('monospace', 12)).Read()    

    
# PCIe, different of power states and resets
def test_power_and_reset(pcie, nvme0, subsystem):
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

    subsystem.poweroff()
    subsystem.poweron()
    nvme0.reset()              # controller reset: CC.EN
    nvme0.getfeatures(7).waitdone()


# test parameters, leverage innovations in python community
@pytest.mark.parametrize("io_count", [1, 9])
@pytest.mark.parametrize("lba_count", [1, 8])
@pytest.mark.parametrize("lba_offset", [0, 8])
def test_different_io_size_and_count(nvme0, nvme0n1,
                                     lba_offset, lba_count, io_count):
    # IO Qpair for IO commands
    io_qpair = d.Qpair(nvme0, 64)

    # allcoate all DMA buffers for IO commands
    bufs = []
    for i in range(io_count):
        bufs.append(d.Buffer(lba_count*512))

    # send and reap all IO command dwords
    for i in range(io_count):
        nvme0n1.read(io_qpair, bufs[i], lba_offset, lba_count)
    io_qpair.waitdone(io_count)


# IO commands, fused operations, generic commands
def test_fused_operations(nvme0, nvme0n1):
    # create qpair and buffer for IO commands
    q = d.Qpair(nvme0, 10)
    b = d.Buffer()
    
    # separate compare and write commands
    nvme0n1.write(q, b, 8).waitdone()
    nvme0n1.compare(q, b, 8).waitdone()

    # implement fused compare and write operations with generic commands
    # Controller.send_cmd() sends admin commands,
    # and Namespace.send_cmd() here sends IO commands. 
    nvme0n1.send_cmd(5|(1<<8), q, b, 1, 8, 0, 0)
    nvme0n1.send_cmd(1|(1<<9), q, b, 1, 8, 0, 0)
    q.waitdone(2)

    
# protocol tests on queue, buffer, PRP, and doorbells
from psd import IOCQ, IOSQ, PRP, PRPList, SQE, CQE
def test_send_cmd_2sq_1cq(nvme0):
    # 2 SQ share one CQ
    cq = IOCQ(nvme0, 1, 10, PRP())
    sq1 = IOSQ(nvme0, 1, 10, PRP(), cqid=1)
    sq2 = IOSQ(nvme0, 2, 16, PRP(), cqid=1)

    # write lba0, 16K data organized by PRPList
    write_cmd = SQE(1, 1)       # write to namespace 1
    write_cmd.prp1 = PRP()      # PRP1 is a 4K page
    prp_list = PRPList()        # PRPList contains 3 pages
    prp_list[0] = PRP()     
    prp_list[1] = PRP()
    prp_list[2] = PRP()
    write_cmd.prp2 = prp_list   # PRP2 points to the PRPList
    write_cmd[10] = 0           # starting LBA
    write_cmd[12] = 31          # LBA count: 32, 16K, 4 pages
    write_cmd.cid = 123         # verify cid later

    # send write commands in both SQ
    sq1[0] = write_cmd          # fill command dwords in SQ1
    write_cmd.cid = 567         # verify cid later
    sq2[0] = write_cmd          # fill command dwords in SQ2
    sq2.tail = 1                # ring doorbell of SQ2 first
    time.sleep(0.1)             # delay to ring SQ1, 
    sq1.tail = 1                #  so command in SQ2 should complete first

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
