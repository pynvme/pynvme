import time
import pytest
import logging

import nvme as d


def test_quarch_dirty_power_cycle_single(nvme0, nvme0n1, subsystem, buf, verify):
    # get the unsafe shutdown count before test
    nvme0.getlogpage(2, buf, 512).waitdone()
    orig_unsafe_count = buf.data(159, 144)
    logging.info("unsafe shutdowns: %d" % orig_unsafe_count)
    assert verify == True

    # 128K random write
    cmdlog_list = [None]*1000
    with nvme0n1.ioworker(io_size=256,
                          lba_random=True,
                          read_percentage=30, 
                          region_end=256*1000*1000,
                          time=30,
                          qdepth=1024, 
                          output_cmdlog_list=cmdlog_list):
        # sudden power loss before the ioworker end
        time.sleep(10)
        subsystem.poweroff()

    # power on and reset controller
    time.sleep(5)
    subsystem.poweron()
    time.sleep(0)
    nvme0.reset()

    # verify unsafe shutdown count
    logging.info(cmdlog_list[-10:])
    nvme0.getlogpage(2, buf, 512).waitdone()
    unsafe_count = buf.data(159, 144)
    logging.info("unsafe shutdowns: %d" % unsafe_count)
    assert unsafe_count == orig_unsafe_count+1

    # verify data in cmdlog_list
    read_buf = d.Buffer(256*512)
    qpair = d.Qpair(nvme0, 1024)
    for cmd in cmdlog_list:
        slba = cmd[0]
        nlba = cmd[1]
        op = cmd[2]
        if nlba:
            def read_cb(cdw0, status1):
                nonlocal slba
                if status1>>1:
                    logging.info("slba 0x%x, status 0x%x" % (slba, status1>>1))
            #logging.info("verify slba 0x%x, nlba %d" % (slba, nlba))
            nvme0n1.read(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
            # re-write to clear CRC mismatch
            nvme0n1.write(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
    qpair.delete()
    
        
# define the power on/off funciton
class quarch_power:
    def __init__(self, url: str, event: str, port: int):
        self.url = url
        self.event = event
        self.port = port
        
    def __call__(self):
        import quarchpy
        logging.debug("power %s by quarch device %s on port %d" %
                      (self.event, self.url, self.port))
        pwr = quarchpy.quarchDevice(self.url)
        
        if self.port == None:
            # serial port
            if self.event == "down":
                # cut down power with data link at the same time
                pwr.sendCommand("signal:all:source 7")
            pwr.sendCommand("run:power %s" % self.event)
        else:
            # network 4-port
            if self.event == "down":
                # cut down power with data link at the same time
                pwr.sendCommand("signal:all:source 7 <%d>" % self.port)
            pwr.sendCommand("run:power %s <%d>" % (self.event, self.port))
            
        pwr.closeConnection()
        
# test multiple devices one by one in multiple loops with quarch power module
device_list = {
    "0000:3d:00.0": (None, None),  # pynvme's software-defined power cycle
    "0000:08:00.0":
    (quarch_power("SERIAL:/dev/ttyUSB0", "up", None),
     quarch_power("SERIAL:/dev/ttyUSB0", "down", None)),
    "0000:01:00.0":
    (quarch_power("REST:192.168.1.11", "up", 4),
     quarch_power("REST:192.168.1.11", "down", 4)),
    "0000:55:00.0":
    (quarch_power("REST:192.168.1.11", "up", 1),
     quarch_power("REST:192.168.1.11", "down", 1)),
    "0000:51:00.0":
    (quarch_power("REST:192.168.1.11", "up", 3),
     quarch_power("REST:192.168.1.11", "down", 3)),
}

@pytest.mark.parametrize("repeat", range(10))
def test_quarch_dirty_power_cycle_multiple(pciaddr, nvme0, repeat):
    poweron, poweroff = device_list[pciaddr]
    
    # run the test one by one
    buf = d.Buffer(4096)
    nvme0n1 = d.Namespace(nvme0, 1, 256*1000*1000)
    subsystem = d.Subsystem(nvme0, poweron, poweroff)
    assert True == nvme0n1.verify_enable(True)

    # enable inline data verify in the test
    logging.info("testing device %s" % pciaddr)
    test_quarch_dirty_power_cycle_single(nvme0, nvme0n1, subsystem, buf, True)
    nvme0n1.close()
    

#TODO: set CC.SHN and dirty shutdown

