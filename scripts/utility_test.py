import time
import pytest
import logging

import nvme as d
import PySimpleGUI as sg
from pytemperature import k2c


def test_format(nvme0: d.Controller, nvme0n1):
    nvme0.format(0).waitdone()


def test_download_firmware(nvme0):
    filename = sg.PopupGetFile('select the firmware binary file', 'pynvme')
    if filename:        
        logging.info("To download firmware binary file: " + filename)
        nvme0.downfw(filename)
    

def test_powercycle_by_sleep(subsystem):
    # sleep system for 10 seconds, to make DUT power off and on
    subsystem.power_cycle()


def test_get_current_temperature(nvme0):
    smart_log = d.Buffer()
    nvme0.getlogpage(0x02, smart_log, 512).waitdone()
    ktemp = smart_log.data(2, 1)
    logging.info("current temperature in SMART data: %0.2f degreeC" % k2c(ktemp))


def sg_show_hex_buffer(buf):
    layout = [ [sg.OK(), sg.Cancel()],
               [sg.Multiline(buf.dump(),
                             enter_submits=True,
                             disabled=True, 
                             size=(80, 25))]
             ]
    sg.Window(str(buf), layout, font=('monospace', 12)).Read()

    
def test_controller_identify_data(nvme0):
    b = d.Buffer(4096, "controller identify data")
    nvme0.identify(b).waitdone()
    sg_show_hex_buffer(b)


def test_namespace_identify_data(nvme0):
    b = d.Buffer(4096, "namespace identify data")
    nvme0.identify(b, 1, 0).waitdone()
    sg_show_hex_buffer(b)


def test_read_lba_data(nvme0, nvme0n1):
    lba = sg.PopupGetText("Which LBA to read?", "pynvme")
    lba = int(lba, 0)  # convert to number
    q = d.Qpair(nvme0, 10)
    b = d.Buffer(512, "LBA 0x%08x" % lba)
    nvme0n1.read(q, b, lba).waitdone()
    sg_show_hex_buffer(b)

    
def test_sanitize(nvme0, nvme0n1, buf):
    if nvme0.id_data(331, 328) == 0:
        warnings.warn("sanitize operation is not supported")
        return

    logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))
    nvme0.sanitize().waitdone()

    # sanitize status log page
    nvme0.getlogpage(0x81, buf, 20).waitdone()
    while buf.data(3, 2) & 0x7 != 1:  # sanitize is not completed
        progress = buf.data(1, 0)*100//0xffff
        sg.OneLineProgressMeter('sanitize progress', progress, 100,
                                'progress', orientation='h')
        nvme0.getlogpage(0x81, buf, 20).waitdone()
        time.sleep(1)

        
def test_get_dell_smart_attributes(nvme0):
    smart = d.Buffer()
    nvme0.getlogpage(0xCA, smart, 512).waitdone()

    l = []
    l.append('Byte | Value | Attribute')
    l.append('   0 |  %3d  | Re-Assigned Sector Count' % smart.data(0))
    l.append('   1 |  %3d  | Program Fail Count (Worst Case Component)' % smart.data(1))
    l.append('   2 |  %3d  | Program Fail Count (SSD Total)' % smart.data(2))
    l.append('   3 |  %3d  | Erase Fail Count (Worst Case Component)' % smart.data(3))
    l.append('   4 |  %3d  | Erase Fail Count (SSD Total)' % smart.data(4))
    l.append('   5 |  %3d  | Wear Leveling Count' % smart.data(5))
    l.append('   6 |  %3d  | Used Reserved Block Count (Worst Case Component)' % smart.data(6))
    l.append('   7 |  %3d  | Used Reserved Block Count (SSD Total)' % smart.data(7))
    l.append('11:8 |  %3d  | Reserved Block Count (SSD Total)' % smart.data(11, 8))

    layout = [[sg.Listbox(l, size=(70, 10))]]
    sg.Window("Dell SMART Attributes",
              layout+[[sg.OK()]],
              font=('monospace', 16)).Read()
