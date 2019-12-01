import time
import pytest
import logging
import nvme as d
from psd import IOCQ, IOSQ, PRP, PRPList, SQE, CQE


def test_pcie_pmcr(pcie):
    pmcr_addr = pcie.cap_offset(0x01)
    pmcr = pcie.register(pmcr_addr, 4)
    logging.info("pmcr register [0x%x]= 0x%x"% (pmcr_addr, pmcr))
    logging.info("Version: %d" % ((pmcr>>16)&7))
    logging.info("AUX currect %d" % ((pmcr>>22)&7))

    
def test_pcie_pmcsr(pcie):
    pmcsr_addr = pcie.cap_offset(0x01)+4
    pmcsr = pcie.register(pmcsr_addr, 4)
    logging.info("pmcsr register [0x%x]= 0x%x"% (pmcsr_addr, pmcsr))
    logging.info("power state %d" % ((pmcsr>>0)&3))
    logging.info("no soft reset: %d" % ((pmcsr>>3)&1))

    scale = (pmcsr>>13)&0x3
    if scale:
        data = (pmcsr>>24)&0xff
        logging.info("D0 power consumption: %d mW" % (data*1000*(0.1**scale)))
    

def test_pcie_pcie_cap(pcie):
    pciecap_addr = pcie.cap_offset(0x10)
    pciecap = pcie.register(pciecap_addr, 4)
    logging.info("pcie capability register [0x%x]= 0x%x"% (pciecap_addr, pciecap))
    logging.info("capability version: %d" % ((pciecap>>16)&0x7))
    logging.info("device type: %d" % ((pciecap>>20)&0xf))
    logging.info("slot: %d" % ((pciecap>>24)&0x1))

    devcap = pcie.register(pciecap_addr+4, 4)
    logging.info("device capability register: 0x%x" % devcap)
    logging.info("Max_Payload_Size Supported: %d Byte" % (128*(2**(devcap&0x7))))

    devctrl = pcie.register(pciecap_addr+8, 2)
    logging.info("device control register: 0x%x" % devctrl)
    logging.info("relaxed ordering: %d" % ((devctrl>>4)&1))
    logging.info("Max_Payload_Size: %d Byte" % (128*(2**((devctrl>>5)&0x7))))
    logging.info("Max_Read_Request_Size: %d Byte" % (128*(2**((devctrl>>12)&0x7))))

    devsts = pcie.register(pciecap_addr+10, 2)
    logging.info("device status register: 0x%x" % devsts)
    pcie[pciecap_addr+10] = 1
    devsts = pcie.register(pciecap_addr+10, 2)
    logging.info("cleared correectable error detected bit")
    logging.info("device status register: 0x%x" % devsts)

    
def test_pcie_link_capabilities_and_status(pcie):
    linkcap_addr = pcie.cap_offset(0x10)+12
    linkcap = pcie.register(linkcap_addr, 4)
    logging.info("link capability register [0x%x]= 0x%x"% (linkcap_addr, linkcap))    
    logging.info("max link speed: %d"% ((linkcap>>0)&0xf))
    logging.info("max link width: %d"% ((linkcap>>4)&0x3f))
    logging.info("ASPM Support: %d"% ((linkcap>>10)&0x3))

    linkctrl_addr = pcie.cap_offset(0x10)+16
    linkctrl = pcie.register(linkctrl_addr, 2)
    logging.info("link control register [0x%x]= 0x%x"% (linkctrl_addr, linkctrl))    
    
    linksts_addr = pcie.cap_offset(0x10)+18
    linksts = pcie.register(linkcap_addr, 2)
    logging.info("link status register [0x%x]= 0x%x"% (linksts_addr, linksts))
    logging.info("link speed: %d"% ((linksts>>0)&0xf))
    logging.info("link width: %d"% ((linksts>>4)&0x3f))
    logging.info("link training: %d"% ((linksts>>11)&0x1))
    logging.info("link active: %d"% ((linksts>>13)&0x1))

    
@pytest.mark.parametrize("aspm", [0, 2])
def test_pcie_link_control_aspm(nvme0, pcie, aspm): #1:0
    linkctrl_addr = pcie.cap_offset(0x10)+16
    linkctrl = pcie.register(linkctrl_addr, 2)
    logging.info("link control register [0x%x]= 0x%x" % (linkctrl_addr, linkctrl))

    # set ASPM control
    pcie[linkctrl_addr] = (linkctrl&0xfc)|aspm
    linkctrl = pcie.register(linkctrl_addr, 2)
    logging.info("link control register [0x%x]= 0x%x" % (linkctrl_addr, linkctrl))

    # IO queue for read commands
    cq = IOCQ(nvme0, 1, 16, PRP())
    sq = IOSQ(nvme0, 1, 16, PRP(), cqid=1)

    # read lba 0 for 1000 times, interleaved with delays
    read_cmd = SQE(2, 1)
    read_cmd.prp1 = PRPList()
    pbit = 1
    for i in range(1000):
        logging.debug(i)
        slot = i%16
        if slot == 0:
            pbit = not pbit
        next_slot = slot+1
        if next_slot == 16:
            next_slot = 0
        sq[slot] = read_cmd
        sq.tail = next_slot
        while cq[slot].p == pbit: pass
        cq.head = next_slot

        # delay to trigger ASPM
        time.sleep(0.01)

    sq.delete()
    cq.delete()

    time.sleep(1)
    

def test_pcie_pmcsr_d3hot(pcie):
    pm_offset = pcie.cap_offset(1)
    pmcs = pcie[pm_offset+4]
    logging.info("pmcs %x" % pmcs)

    # set d3hot
    pcie[pm_offset+4] = pmcs|3     #D3hot
    pmcs = pcie[pm_offset+4]
    logging.info("pmcs %x" % pmcs)

    # and exit d3hot
    time.sleep(1)
    pcie[pm_offset+4] = pmcs&0xfc  #D0
    pmcs = pcie[pm_offset+4]
    logging.info("pmcs %x" % pmcs)

def test_pcie_cold_reset(subsystem):
    subsystem.power_cycle()

def test_pcie_reset(pcie):
    pcie.reset()
    
def test_controller_reset(nvme0, pcie):
    test_pcie_pmcsr_d3hot(pcie)
    nvme0.reset()

def test_subsystem_reset(subsystem, pcie):
    subsystem.reset()

def test_pcie_aspm_off_and_d3hot(pcie, nvme0n1):
    assert pcie.aspm == 0
    pcie.power_state = 3
    time.sleep(1)
    pcie.power_state = 0
    assert pcie.aspm == 0
    nvme0n1.ioworker(io_size=2, time=2).start().close()
    
    
    
