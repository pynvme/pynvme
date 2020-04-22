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


def test_read_lba_data(nvme0):
    lba = int(sg.PopupGetText("Which LBA to read?", "pynvme"))
    q = d.Qpair(nvme0, 10)
    b = d.Buffer(512, "LBA 0x%08x" % lba)
    nvme0n1 = d.Namespace(nvme0)
    nvme0n1.read(q, b, lba).waitdone()
    sg_show_hex_buffer(b)

        
def test_get_dell_smart_attributes(nvme0):
    smart = d.Buffer()
    nvme0.getlogpage(0xCA, smart, 512).waitdone()

    l = []
    l.append('Byte |  Value  | Attribute')
    l.append('   0 |  %5d  | Re-Assigned Sector Count' % smart.data(0))
    l.append('   1 |  %5d  | Program Fail Count (Worst Case Component)' % smart.data(1))
    l.append('   2 |  %5d  | Program Fail Count (SSD Total)' % smart.data(2))
    l.append('   3 |  %5d  | Erase Fail Count (Worst Case Component)' % smart.data(3))
    l.append('   4 |  %5d  | Erase Fail Count (SSD Total)' % smart.data(4))
    l.append('   5 |  %5d  | Wear Leveling Count' % smart.data(5))
    l.append('   6 |  %5d  | Used Reserved Block Count (Worst Case Component)' % smart.data(6))
    l.append('   7 |  %5d  | Used Reserved Block Count (SSD Total)' % smart.data(7))
    l.append('11:8 |  %5d  | Reserved Block Count (SSD Total)' % smart.data(11, 8))

    layout = [[sg.Listbox(l, size=(70, 10))]]
    sg.Window("Dell SMART Attributes",
              layout+[[sg.OK()]],
              font=('monospace', 16)).Read()


def test_get_smart_health_information(nvme0):
    smart = d.Buffer()
    nvme0.getlogpage(0x02, smart, 512).waitdone()

    l = []
    l.append('  Byte |   Value   | Attribute')
    l.append('     0 |  %7d  | Critical Warning' % smart.data(0))
    l.append('  2: 1 |  %7d  | Composite Temperature (degree C)' % k2c(smart.data(2, 1)))
    l.append('     3 |  %7d  | Available Spare' % smart.data(3))
    l.append('     4 |  %7d  | Available Spare Threshold' % smart.data(4))
    l.append('     5 |  %7d  | Percentage Used' % smart.data(5))
    l.append('     6 |  %7d  | Endurance Group Critical Warning Summary' % smart.data(6))
    l.append(' 47:32 |%11d| Data Units Read (1000LBA)' % smart.data(47, 32))
    l.append(' 63:48 |%11d| Data Units Written (1000LBA)' % smart.data(63, 48))
    l.append(' 79:64 |%11d| Host Read Commands' % smart.data(79, 64))
    l.append(' 95:80 |%11d| Host Write Commands' % smart.data(95, 80))
    l.append('111:96 |  %7d  | Controller Busy Time (minutes)' % smart.data(111, 96))
    l.append('127:112|  %7d  | Power Cycles' % smart.data(127, 112))
    l.append('143:128|  %7d  | Power On Hours' % smart.data(143, 128))
    l.append('159:144|  %7d  | Unsafe Shutdowns' % smart.data(159, 144))
    l.append('175:160|  %7d  | Media and Data Integrity Errors' % smart.data(175, 160))
    l.append('191:176|  %7d  | Number of Error Information Log Entries' % smart.data(191, 176))
    l.append('195:192|  %7d  | Warning Composite Temperature Time (minutes)' % smart.data(195, 192))
    l.append('199:196|  %7d  | Critical Composite Temperature Time (minutes)' % smart.data(199, 196))
    l.append('201:200|  %7d  | Temperature Sensor 1 (degree C)' % k2c(smart.data(201, 200)))
    l.append('203:202|  %7d  | Temperature Sensor 2 (degree C)' % k2c(smart.data(203, 202)))
    l.append('205:204|  %7d  | Temperature Sensor 3 (degree C)' % k2c(smart.data(205, 204)))
    l.append('207:206|  %7d  | Temperature Sensor 4 (degree C)' % k2c(smart.data(207, 206)))
    l.append('209:208|  %7d  | Temperature Sensor 5 (degree C)' % k2c(smart.data(209, 208)))
    l.append('211:210|  %7d  | Temperature Sensor 6 (degree C)' % k2c(smart.data(211, 210)))
    l.append('213:212|  %7d  | Temperature Sensor 7 (degree C)' % k2c(smart.data(213, 212)))
    l.append('215:214|  %7d  | Temperature Sensor 8 (degree C)' % k2c(smart.data(215, 214)))
    l.append('219:216|  %7d  | Thermal Management Temperature 1 Transition Count' % smart.data(219, 216))
    l.append('223:220|  %7d  | Thermal Management Temperature 2 Transition Count' % smart.data(223, 220))
    l.append('227:224|  %7d  | Total Time For Thermal Management Temperature 1' % smart.data(227, 224))
    l.append('231:228|  %7d  | Total Time For Thermal Management Temperature 2' % smart.data(231, 228))

    layout = [[sg.Listbox(l, size=(70, 20))]]
    sg.Window("SMART/Health Information",
              layout+[[sg.OK()]],
              font=('monospace', 16)).Read()


def test_get_log_page(nvme0, lid=None):
    if lid == None:
        lid = int(sg.PopupGetText("Which Log ID to read?", "pynvme"))
    lbuf = d.Buffer(512, "%s, Log ID: %d" % (nvme0.id_data(63, 24, str), lid))
    nvme0.getlogpage(lid, lbuf).waitdone()
    sg_show_hex_buffer(lbuf)

    
def test_firmware_slot(nvme0, subsystem):
    filename = sg.PopupGetFile('select the firmware binary file', 'pynvme')
    if not filename:
        pytest.skip("no binary file found")

    def get_fw_slot(): #return: next reset, current
        buf = d.Buffer(512)
        nvme0.getlogpage(3, buf).waitdone()
        return buf[1], buf[0]
    
    # download slot 1
    nvme0.downfw(filename, 1)
    next_slot, this_slot = get_fw_slot()
    assert next_slot == 1

    # reset to activate
    subsystem.power_cycle()
    next_slot, this_slot = get_fw_slot()
    assert this_slot == 1
    assert next_slot == 0
