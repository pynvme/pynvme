#
#  BSD LICENSE
#
#  Copyright (c) Crane Chu <cranechu@gmail.com>
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#    * Neither the name of Intel Corporation nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-


import time
import pytest
import logging

import nvme as d


def test_format(nvme0: d.Controller, nvme0n1):
    nvme0.format(0).waitdone()
    nvme0n1.format(512)


def test_download_firmware(nvme0):
    import PySimpleGUI as sg
    filename = sg.PopupGetFile('select the firmware binary file', 'pynvme')
    if filename:        
        logging.info("To download firmware binary file: " + filename)
        nvme0.downfw(filename)
    

def test_powercycle_by_sleep(subsystem, nvme0):
    # sleep system for 10 seconds, to make DUT power off and on
    subsystem.power_cycle()


def test_get_current_temperature(nvme0):
    from pytemperature import k2c
    smart_log = d.Buffer()
    nvme0.getlogpage(0x02, smart_log, 512).waitdone()
    ktemp = smart_log.data(2, 1)
    logging.info("current temperature in SMART data: %0.2f degreeC" % k2c(ktemp))


def sg_show_hex_buffer(buf):
    import PySimpleGUI as sg
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


def test_read_lba_data(nvme0, nvme0n1, qpair):
    import PySimpleGUI as sg
    
    lba = int(sg.PopupGetText("Which LBA to read?", "pynvme"))
    b = d.Buffer(512, "LBA 0x%08x" % lba)
    nvme0n1.read(qpair, b, lba).waitdone()
    sg_show_hex_buffer(b)

        
def test_get_dell_smart_attributes(nvme0):
    import PySimpleGUI as sg
    
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
    from pytemperature import k2c
    import PySimpleGUI as sg
    
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
    import PySimpleGUI as sg
    
    if lid == None:
        lid = int(sg.PopupGetText("Which Log ID to read?", "pynvme"))
    lbuf = d.Buffer(512, "%s, Log ID: %d" % (nvme0.id_data(63, 24, str), lid))
    nvme0.getlogpage(lid, lbuf).waitdone()
    sg_show_hex_buffer(lbuf)

    
def test_firmware_slot(nvme0, subsystem):
    import PySimpleGUI as sg
    
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
    nvme0.reset()
    next_slot, this_slot = get_fw_slot()
    assert this_slot == 1
    assert next_slot == 0

    
def test_list_power_states(nvme0, buf):
    #according to NVMe Spec 1.4, Figure 247 and 248
    def print_ps(buf, ps):
        offset = 2048 + ps*32
        if buf.data(offset+1, offset+0):
            logging.info("PS %d" % ps)
            logging.info("===================================")
            
            ps_table = {0: 0, 0x40: 0.0001, 0x80: 0.01}
            mxps = 0.0001 if buf[offset+3]&1 else 0.01
            nops = 'Non-' if buf[offset+3]&2 else ''
            logging.info("Maximum Power: %.3f W" % (buf.data(offset+1, offset+0)*mxps))
            logging.info(nops+"Opertional State")

            logging.info("Entry Lantecy: %dus" %(buf.data(offset+7, offset+4)))
            logging.info("Exit Lantecy: %dus" %(buf.data(offset+11, offset+8)))

            logging.info("Relative Read Throughput: %d" %(buf.data(offset+12)))
            logging.info("Relative Read Latency: %d" %(buf.data(offset+13)))
            logging.info("Relative Write Throughput: %d" %(buf.data(offset+14)))
            logging.info("Relative Write Latency: %d" %(buf.data(offset+15)))

            ips = ps_table[buf[offset+18]]
            logging.info("Idle Power: %.3f W" % (buf.data(offset+17, offset+16)*ips))
            
            aps = ps_table[buf[offset+22]&0xc0]
            logging.info("Active Power: %.3f W with Workload %d" % (buf.data(offset+21, offset+20)*aps, buf[offset+22]&0x7))
            logging.info("")
        
    nvme0.identify(buf).waitdone()
    for ps in range(32):
        print_ps(buf, ps)
