import pytest
import nvme as d

import time
import logging


# intuitive, vscode, debug, cmdlog, IDE
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
    

# simple ioworker, complicated io_size
def test_ioworker_simplified(nvme0, nvme0n1):
    nvme0n1.ioworker(io_size=[1, 2, 3, 7, 8, 16], time=1).start().close()
    test_hello_world(nvme0, nvme0n1)

    
# ioworker interleaved with admin commands, pythonic, CPU, log, fio
def test_ioworker_with_temperature(nvme0, nvme0n1):
    smart_log = d.Buffer(512, "smart log")
    with nvme0n1.ioworker(io_size=8, lba_align=16,
                          lba_random=True, qdepth=16,
                          read_percentage=0, time=30):
        for i in range(40):
            nvme0.getlogpage(0x02, smart_log, 512).waitdone()
            ktemp = smart_log.data(2, 1)
            
            from pytemperature import k2c
            logging.info("temperature: %0.2f degreeC" % k2c(ktemp))
            time.sleep(1)


# multiple ioworkers, PCIe, TCP, CPU, performance
def test_multiple_controllers_and_namespaces():
    # address list of the devices to test
    addr_list = [b'02:00.0', b'03:00.0', b'192.168.0.3', b'127.0.0.1:4420']
    test_seconds = 10
    
    nvme_list = [d.Controller(a) for a in addr_list]
    ns_list = [d.Namespace(n) for n in nvme_list]

    # operations on multiple controllers
    for nvme in nvme_list:
        logging.info("device: %s" % nvme.id_data(63, 24, str))

    # format for faster read
    for ns in ns_list:
        ns.format(512)
        
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
    

# GUI, productivity
import PySimpleGUI as sg
def test_get_log_page(nvme0):
    lid = int(sg.PopupGetText("Which Log ID to read?", "pynvme"))
    buf = d.Buffer(512, "%s, Log ID: %d" % (nvme0.id_data(63, 24, str), lid))
    nvme0.getlogpage(lid, buf).waitdone()
    
    layout = [ [sg.OK(), sg.Cancel()],
               [sg.Multiline(buf.dump(), enter_submits=True, disabled=True, size=(80, 25))] ]
    sg.Window(str(buf), layout, font=('monospace', 12)).Read()    

    
# different of power states and resets
def test_power_and_reset(pcie, nvme0, subsystem):
    pcie.aspm = 2              # ASPM L1
    pcie.power_state = 3       # PCI PM D3hot
    pcie.aspm = 0
    pcie.power_state = 0
    nvme0.reset()              # controller reset
    pcie.reset()               # PCIe reset
    subsystem.reset()          # NVMe subsystem reset
    subsystem.power_cycle(10)  #power cycle NVMe device, aka: cold reset


# access PCIe/NVMe registers, pythonic
def test_registers(pcie, nvme0):
    logging.info("0x%x, 0x%x" % (pcie[0], pcie.register(0, 2)))
    logging.info("0x%08x, 0x%08x" % (nvme0[0], nvme0[4]))


# test parameter, qpair
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
