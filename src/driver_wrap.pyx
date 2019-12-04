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


#!/usr/bin/python3
# -*- coding: utf-8 -*-
#cython: linetrace=True
#cython: language_level=3
#cython: embedsignature=True

# for generating api.md only
##cython: binding=True


# python package
import os
import sys
import time
import glob
import math
import atexit
import signal
import struct
import random
import logging
import warnings
import datetime
import statistics
import subprocess
import multiprocessing

# c library
import cython
from libc.string cimport strncpy, memset, strlen
from libc.stdio cimport printf
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from cpython.exc cimport PyErr_CheckSignals

# c driver
cimport cdriver as d


# module informatoin
__author__ = "Crane Chu"
__version__ = "1.6"


# random seed in all processes
_random_seed = 0

# nvme command timeout, it's a warning
# drive times out earlier than driver timeout
_cTIMEOUT = 10
_timeout_happened = False
cdef void timeout_driver_cb(void* cb_arg, d.ctrlr* ctrlr,
                            d.qpair * qpair, unsigned short cid):
    _timeout_happened = True
    error_string = "drive timeout: qpair: %d, cid: %d" % \
        (d.qpair_get_id(qpair), cid)
    warnings.warn(error_string)


def _timeout_signal_handler(signum, frame):
    error_string = "pynvme timeout in driver"
    _reentry_flag_init()
    raise TimeoutError(error_string)


# prevent waitdone reentry
def _reentry_flag_init():
    global _reentry_flag
    _reentry_flag = False


# for abrupt exit
def _interrupt_handler(signal, frame):
    logging.debug("terminated.")
    sys.exit(0)


# handle completion dwords in callback from c
cdef struct _cpl:
    unsigned int cdw0
    unsigned int rsvd1
    unsigned short sqhead
    unsigned short sqid
    unsigned short cid
    unsigned short status1  #this word actully inculdes some other bites


cdef void cmd_cb(void* f, const d.cpl* cpl):
    arg = <_cpl*>cpl  # no qa
    status1 = arg.status1
    func = <object>f   # no qa

    if func is not None:
        # call script callback function to check cpl
        try:
            func(arg.cdw0, status1)
        except AssertionError as e:
            warnings.warn("ASSERT: "+str(e))

    if d.nvme_cpl_is_error(cpl):
        # script not check, so driver check cpl
        sc = (status1>>1) & 0xff
        sct = (status1>>9) & 0x7
        warnings.warn("ERROR status: %02x/%02x" % (sct, sc))


cdef void aer_cmd_cb(void* f, const d.cpl* cpl):
    arg = <_cpl*>cpl  # no qa
    logging.warning("AER triggered, dword0: 0x%x" % arg.cdw0)
    warnings.warn("AER notification is triggered")
    cmd_cb(f, cpl)


cdef class Buffer(object):
    """Buffer allocates memory in DPDK, so we can get its physical address for DMA. Data in buffer is clear to 0 in initialization.

    # Parameters
        size (int): the size (in bytes) of the buffer. Default: 4096
        name (str): the name of the buffer. Default: 'buffer'
        pvalue (int): data pattern value. Default: 0
        ptype (int): data pattern type. Default: 0

    # data patterns
```md
        |ptype    | pvalue                                                     |
        |---------|------------------------------------------------------------|
        |0        | 0 for all-zero data, 1 for all-one data                    |
        |32       | 32-bit value of the repeated data pattern                  |
        |0xbeef   | random data compressed rate (0: all 0; 100: fully random)  |
        |others   | not supported                                              |
```

    # Examples
```python
        >>> b = Buffer(1024, 'example')
        >>> b[0] = 0x5a
        >>> b[1:3] = [1, 2]
        >>> b[4:] = [10, 11, 12, 13]
        >>> b.dump(16)
        example
        00000000  5a 01 02 00 0a 0b 0c 0d  00 00 00 00 00 00 00 00   Z...............
        >>> b[:8:2]
        b'Z\\x02\\n\\x0c'
        >>> b.data(2) == 2
        True
        >>> b[2] == 2
        True
        >>> b.data(2, 0) == 0x02015a
        True
        >>> len(b)
        1024
        >>> b
        <buffer name: example>
        >>> b[8:] = b'xyc'
        example
        00000000  5a 01 02 00 0a 0b 0c 0d  78 79 63 00 00 00 00 00   Z.......xyc.....
        >>> b.set_dsm_range(1, 0x1234567887654321, 0xabcdef12)
        >>> b.dump(64)
        buffer
        00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  ................
        00000010  00 00 00 00 12 ef cd ab  21 43 65 87 78 56 34 12  ........!Ce.xV4.
        00000020  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  ................
        00000030  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ................
```
    """

    cdef void* ptr
    cdef size_t size
    cdef char* name
    cdef unsigned long phys_addr

    def __cinit__(self, size=4096, name="buffer", pvalue=0, ptype=0):
        assert size > 0, "0 is not valid size"

        # copy python string to c string
        name_len = (len(name)+1)*sizeof(char)
        self.name = <char*>PyMem_Malloc(name_len)
        if not self.name:
            raise MemoryError()
        memset(self.name, 0, name_len)
        strncpy(self.name, name.encode('ascii'), len(name))

        # buffer init
        self.size = size
        self.ptr = d.buffer_init(size, &self.phys_addr, ptype, pvalue)
        if self.ptr is NULL:
            raise MemoryError()

    def __dealloc__(self):
        if self.name is not NULL:
            PyMem_Free(self.name)

        if self.ptr is not NULL:
            d.buffer_fini(self.ptr)

    @property
    def data_head(self):
        return self.dump().split('\n')[0][:-2].encode('ascii')

    @property
    def data_tail(self):
        return self.dump().split('\n')[-2][:-2].encode('ascii')

    @property
    def phys_addr(self):
        """physical address of the buffer"""

        return self.phys_addr

    def dump(self, size=None):
        """get the buffer content

        # Parameters
            size (int): the size of the buffer to print. Default: None, means to print the whole buffer
        """
        if self.ptr and self.size:
            # 0 size means print the whole buffer
            if size is None or size > self.size:
                size = self.size
            dbuf = d.log_buf_dump(self.name, self.ptr, size)
            return dbuf.decode('ascii')

    def data(self, byte_end, byte_begin=None, type=int):
        """get field in the buffer. Little endian for integers.

        # Parameters
            byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.
            byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
            type (type): the type of the field. It should be int or str. Default: int, convert to integer python object

        # Returns
            (int or str): the data in the specified field
        """

        if byte_begin is None:
            byte_begin = byte_end

        if type is int:
            return int.from_bytes(self[byte_begin:byte_end+1], 'little')
        else:
            assert type is str, "identify data should be int or str"
            return str(self[byte_begin:byte_end+1], "ascii").rstrip()

    def __len__(self):
        return self.size

    def __repr__(self):
        return '<buffer name: %s>' % str(self.name, "ascii")

    def __getitem__(self, index):
        if isinstance(index, slice):
            return bytes([self[i] for i in range(*index.indices(len(self)))])
        elif isinstance(index, int):
            if index >= self.size:
                raise IndexError()
            return (<unsigned char*>self.ptr)[index]
        else:
            raise TypeError()

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            start = 0 if index.start is None else index.start
            for i, d in enumerate(value):
                self[i+start] = d
        elif isinstance(index, int):
            if index >= self.size:
                raise IndexError()
            (<unsigned char*>self.ptr)[index] = value
        else:
            raise TypeError()

    def set_dsm_range(self, index, lba, lba_count):
        """set dsm ranges in the buffer, for dsm/deallocation (a.ka trim) commands

        # Parameters
            index (int): the index of the dsm range to set
            lba (int): the start lba of the range
            lba_count (int): the lba count of the range
        """
        assert type(lba) is int, "parameter must be integer"
        assert type(lba_count) is int, "parameter must be integer"
        self[index*16:(index+1)*16] = struct.pack("<LLQ", 0, lba_count, lba)


cdef class Subsystem(object):
    """Subsystem class. Prefer to use fixture "subsystem" in test scripts.

    # Parameters
        nvme (Controller): the nvme controller object of that subsystem
    """

    cdef Controller _nvme

    def __cinit__(self, Controller nvme):
        self._nvme = nvme

    def power_cycle(self, sec=10):
        """power off and on in seconds

        # Parameters
            sec (int): the seconds between power off and power on
        """

        # use S3/suspend to power off nvme device, and use rtc to power on again
        logging.debug("power off nvme device for %d seconds" % sec)
        subprocess.call("sudo rtcwake -m mem -s %d 1>/dev/null 2>/dev/null" % sec, shell=True)
        logging.debug("power is back")

        #reset driver
        self._nvme.reset()

    def shutdown_notify(self, abrupt=False):
        """notify nvme subsystem a shutdown event through register cc.chn

        # Parameters
            abrupt (bool): it will be an abrupt shutdown (return immediately) or clean shutdown (wait shutdown completely)
        """

        # refer to spec 7.6.2, host delay is recommended
        rtd3e = self._nvme.id_data(91, 88)
        if rtd3e == 0:
            rtd3e = 1000_000

        # cc.chn
        cc = self._nvme[0x14]
        if abrupt:
            cc = cc | 0x8000
        else:
            cc = cc | 0x4000
        self._nvme[0x14] = cc

        # csts.shst: wait shutdown processing is complete
        time.sleep(rtd3e/1000_000)
        while (self._nvme[0x1c] & 0xc) != 0x8: pass
        logging.debug("shutdown completed")

    def reset(self):
        """reset the nvme subsystem through register nssr.nssrc"""

        # nssr.nssrc: nvme subsystem reset
        logging.debug("nvme subsystem reset by NSSR.NSSRC")
        self._nvme[0x20] = 0x4e564d65  # "NVMe"
        Pcie(self._nvme).reset()       # reset PCIe link


cdef class Pcie(object):
    """Pcie class. Prefer to use fixture "pcie" in test scripts

    # Parameters
        nvme (Controller): the nvme controller object of that subsystem
    """

    cdef Controller _nvme
    cdef unsigned short vid
    cdef unsigned short did

    def __cinit__(self, Controller nvme):
        self._nvme = nvme
        self.vid = self.register(0, 2)
        self.did = self.register(2, 2)

    def __getitem__(self, index):
        """access pcie config space by bytes."""
        cdef unsigned char value

        if isinstance(index, slice):
            return [self[ii] for ii in range(index.stop)[index]]
        elif isinstance(index, int):
            d.pcie_cfg_read8(d.pcie_init(self._nvme._ctrlr), & value, index)
            return value
        else:
            raise TypeError()

    def __setitem__(self, index, value):
        """set pcie config space by bytes."""
        if isinstance(index, int):
            d.pcie_cfg_write8(d.pcie_init(self._nvme._ctrlr), value, index)
        else:
            raise TypeError()

    def register(self, offset, byte_count):
        """access registers in pcie config space, and get its integer value.

        # Parameters
            offset (int): the offset (in bytes) of the register in the config space
            byte_count (int): the size (in bytes) of the register

        # Returns
            (int): the value of the register
        """

        assert byte_count <= 8, "support uptp 8-byte PCIe register access"
        value = bytes(self[offset:offset+byte_count])
        return int.from_bytes(value, 'little')

    def cap_offset(self, cap_id):
        """get the offset of a capability

        # Parameters
            cap_id (int): capability id

        # Returns
            (int): the offset of the register, or None if the capability is not existed
        """

        next_offset = self.register(0x34, 1)
        while next_offset != 0:
            value = self.register(next_offset, 2)
            cid = value % 256
            cap_offset = next_offset
            next_offset = value>>8
            if cid == cap_id:
                return cap_offset

        logging.info("cannot find the capability %d" % cap_id)
        
    def reset(self):
        """reset this pcie device"""
        vid = self.vid
        did = self.did
        vdid = '%04x %04x' % (vid, did)
        nvme = 'nvme'
        spdk = 'uio_pci_generic'
        bdf = self._nvme._bdf.decode('utf-8')
        logging.debug("pci reset %s on %s" % (vdid, bdf))

        # hot reset by TS1 TS2
        subprocess.call('./src/pcie_hot_reset.sh %s 2> /dev/null || true' % bdf, shell=True)

        # reset to inbox driver
        subprocess.call('echo "%s" > "/sys/bus/pci/devices/%s/driver/remove_id" 2> /dev/null || true' % (vid, bdf), shell=True)
        subprocess.call('echo "%s" > "/sys/bus/pci/devices/%s/driver/unbind" 2> /dev/null || true' % (bdf, bdf), shell=True)
        subprocess.call('echo "%s" > "/sys/bus/pci/drivers/%s/new_id" 2> /dev/null || true' % (vid, nvme), shell=True)
        subprocess.call('echo "%s" > "/sys/bus/pci/drivers/%s/bind" 2> /dev/null || true' % (bdf, nvme), shell=True)

        # config spdk driver
        subprocess.call('echo "%s" > "/sys/bus/pci/devices/%s/driver/remove_id" 2> /dev/null || true' % (vid, bdf), shell=True)
        subprocess.call('echo "%s" > "/sys/bus/pci/devices/%s/driver/unbind" 2> /dev/null || true' % (bdf, bdf), shell=True)
        subprocess.call('echo "%s" > "/sys/bus/pci/drivers/%s/new_id" 2> /dev/null || true' % (vid, spdk), shell=True)
        subprocess.call('echo "%s" > "/sys/bus/pci/drivers/%s/bind" 2> /dev/null || true' % (bdf, spdk), shell=True)

        # reset driver: namespace is init by every test, so no need reinit
        self._nvme._reinit()

    @property
    def aspm(self):
        """current ASPM setting"""
        
        linkctrl_addr = self.cap_offset(0x10)+16
        return self.register(linkctrl_addr, 2) & 0x3
    
    @aspm.setter
    def aspm(self, control):
        """config new ASPM Control:

        # Parameters
            control: ASPM control field in Link Control register: 
                     b00: ASPM is disabled
                     b01: L0s
                     b10: L1
                     b11: L0s and L1
        """

        assert control < 4 and control >= 0
        linkctrl_addr = self.cap_offset(0x10)+16
        linkctrl = self.register(linkctrl_addr, 2)
        self.__setitem__(linkctrl_addr, (linkctrl&0xfc)|control)

    @property
    def power_state(self):
        """current power state"""
        
        pmcsr_addr = self.cap_offset(1) + 4
        return self.register(pmcsr_addr, 4) & 0x3
    
    @power_state.setter
    def power_state(self, state):
        """config new power state:

        # Parameters
            state: new state of the PCIe device:
                   0: D0
                   1: D1
                   2: D2
                   3: D3hot
        """
        
        assert state < 4 and state >= 0
        pmcsr_addr = self.cap_offset(1) + 4
        pmcsr =  self.register(pmcsr_addr, 4)
        self.__setitem__(pmcsr_addr, (pmcsr&0xfc)|state)
        
    
class NvmeEnumerateError(Exception):
    pass


class NvmeDeletionError(Exception):
    pass


cdef class Controller(object):
    """Controller class. Prefer to use fixture "nvme0" in test scripts.

    # Parameters
        addr (bytes): the bus/device/function address of the DUT, for example: \
                      b'01:00.0' (PCIe BDF address),  \
                      b'127.0.0.1' (TCP IP address).

    # Example
```python
        >>> n = Controller(b'01:00.0')
        >>> hex(n[0])     # CAP register
        '0x28030fff'
        >>> hex(n[0x1c])  # CSTS register
        '0x1'
        >>> n.id_data(23, 4, str)
        'TW0546VPLOH007A6003Y'
        >>> n.supports(0x18)
        False
        >>> n.supports(0x80)
        True
        >>> id_buf = Buffer()
        >>> n.identify().waitdone()
        >>> id_buf.dump(64)
        buffer
        00000000  a4 14 4b 1b 54 57 30 35  34 36 56 50 4c 4f 48 30  ..K.TW0546VPLOH0
        00000010  30 37 41 36 30 30 33 59  43 41 33 2d 38 44 32 35  07A6003YCA3-8D25
        00000020  36 2d 51 31 31 20 4e 56  4d 65 20 4c 49 54 45 4f  6-Q11 NVMe LITEO
        00000030  4e 20 32 35 36 47 42 20  20 20 20 20 20 20 20 20   N 256GB
        >>> n.cmdlog(2)
        driver.c:1451:log_cmd_dump: *NOTICE*: dump qpair 0, latest tail in cmdlog: 1
        driver.c:1462:log_cmd_dump: *NOTICE*: index 0, 2018-10-14 14:52:25.533708
        nvme_qpair.c: 118:nvme_admin_qpair_print_command: *NOTICE*: IDENTIFY (06) sqid:0 cid:0 nsid:1 cdw10:00000001 cdw11:00000000
        driver.c:1469:log_cmd_dump: *NOTICE*: index 0, 2018-10-14 14:52:25.534030
        nvme_qpair.c: 306:nvme_qpair_print_completion: *NOTICE*: SUCCESS (00/00) sqid:0 cid:95 cdw0:0 sqhd:0142 p:1 m:0 dnr:0
        driver.c:1462:log_cmd_dump: *NOTICE*: index 1, 1970-01-01 07:30:00.000000
        nvme_qpair.c: 118:nvme_admin_qpair_print_command: *NOTICE*: DELETE IO SQ (00) sqid:0 cid:0 nsid:0 cdw10:00000000 cdw11:00000000
        driver.c:1469:log_cmd_dump: *NOTICE*: index 1, 1970-01-01 07:30:00.000000
        nvme_qpair.c: 306:nvme_qpair_print_completion: *NOTICE*: SUCCESS (00/00) sqid:0 cid:0 cdw0:0 sqhd:0000 p:0 m:0 dnr:0
```
    """

    cdef d.ctrlr * _ctrlr
    cdef char _bdf[64]
    cdef Buffer hmb_buf
    cdef unsigned int _timeout

    def __cinit__(self, addr):
        strncpy(self._bdf, addr, strlen(addr)+1)
        self._timeout = _cTIMEOUT*1000
        self._create()

    def __dealloc__(self):
        # print("dealloc ctrlr: %x" % <unsigned long>self._ctrlr); sys.stdout.flush()
        self._close()

    def _reinit(self):
        logging.debug("to re-initialize nvme: %s", self._bdf)
        self._close()
        self._create()

    def _create(self):
        # tcp or pci address
        port = 0
        addr = self._bdf.decode('utf-8')
        if ':' not in addr:
            # pure ip address without port
            port = 4420
        else:
            port = addr.split(':')[-1]
            try:
                port = int(port)
                addr = addr.split(':')[0]
            except:
                # invalid port, which should be pci address
                port = 0

        # pcie address, start with domain
        if port == 0 and not os.path.exists("/sys/bus/pci/devices/%s" % addr):
            addr = "0000:"+addr
            
        bdf = addr.encode('utf-8')
        strncpy(self._bdf, bdf, strlen(bdf)+1)
        self._ctrlr = d.nvme_init(bdf, port)
        if self._ctrlr is NULL:
            raise NvmeEnumerateError("fail to create the controller")
        d.nvme_register_timeout_cb(self._ctrlr, timeout_driver_cb, self._timeout)
        self.register_aer_cb(None)
        logging.debug("nvme initialized: %s", self._bdf)

    def _close(self):
        if self._ctrlr is not NULL:
            ret = d.nvme_fini(self._ctrlr)
            if ret != 0:
                raise NvmeDeletionError("fail to close the controller, check if any qpair is not deleted: %d" % ret)
            self._ctrlr = NULL

    def enable_hmb(self):
        """enable HMB function"""

        hmb_size = self.id_data(275, 272)
        if hmb_size:
            self.hmb_buf = Buffer(4096*hmb_size)
            hmb_list_buf = Buffer(4096)
            hmb_list_buf[0:8] = self.hmb_buf.phys_addr.to_bytes(8, 'little')
            hmb_list_buf[8:12] = hmb_size.to_bytes(4, 'little')
            hmb_list_phys = hmb_list_buf.phys_addr
            self.setfeatures(0x0d, 1, hmb_size,
                             hmb_list_phys&0xffffffff,
                             hmb_list_phys>>32, 1).waitdone()

    def disable_hmb(self):
        """disable HMB function """

        self.setfeatures(0x0d, 0).waitdone()

    @property
    def addr(self):
        return self._bdf.decode('utf-8')
    
    @property
    def mdts(self):
        """max data transfer size"""

        page_size = (1UL<<(12+((self[4]>>16)&0xf)))
        mdts_shift = self.id_data(77)
        if mdts_shift == 0:
            return sys.maxsize
        else:
            return page_size*(1UL<<mdts_shift)


    @property
    def cap(self):
        """64-bit CAP register of NVMe"""

        # it is a 64-bit readonly register
        cdef unsigned long value
        d.nvme_get_reg64(self._ctrlr, 0, &value)
        return value


    @property
    def _timeout_pynvme(self):
        # timeout signal in pynvme driver layer by seconds,
        # it's an assert fail, needs longer than drive's timeout
        return self._timeout//1000 + 20


    @property
    def timeout(self):
        """timeout value of this controller in milli-seconds.

        It is configurable by assigning new value in milli-seconds.
        """

        return self._timeout


    @timeout.setter
    def timeout(self, msec):
        """set new timeout time for this controller

        # Parameters
            msec (int): milli-seconds of timeout value
        """

        self._timeout = msec
        d.nvme_register_timeout_cb(self._ctrlr, timeout_driver_cb, self._timeout)


    def __getitem__(self, index):
        """read nvme registers in BAR memory space by dwords."""

        cdef unsigned int value

        assert index % 4 == 0, "only support 4-byte aligned NVMe register read"

        if isinstance(index, int):
            d.nvme_get_reg32(self._ctrlr, index, & value)
            if ~value == 0:
                raise SystemError()
            return value
        else:
            raise TypeError()

    def __setitem__(self, index, value):
        """write nvme registers in BAR memory space by dwords."""

        assert index % 4 == 0, "only support 4-byte aligned NVMe register write"

        if isinstance(index, int):
            d.nvme_set_reg32(self._ctrlr, index, value)
        else:
            raise TypeError()

    def cmdlog(self, count=0):
        """print recent commands and their completions.

        # Parameters
            count (int): the number of commands to print. Default: 0, to print the whole cmdlog
        """

        d.log_cmd_dump_admin(self._ctrlr, count)

    def reset(self):
        """controller reset: cc.en 1 => 0 => 1

        Notice
            Test scripts should delete all io qpairs before reset!
        """

        # reset controller
        self._reinit()

    def cmdname(self, opcode):
        """get the name of the admin command

        # Parameters
            opcode (int): the opcode of the admin command

        # Returns
            (str): the command name
        """

        assert opcode < 256
        name = d.cmd_name(opcode, 0)
        return name.decode('ascii')

    def supports(self, opcode):
        """check if the admin command is supported

        # Parameters
            opcode (int): the opcode of the admin command

        # Returns
            (bool): if the command is supported
        """

        assert opcode < 256*2 # *2 for nvm command set
        logpage_buf = Buffer(4096)
        self.getlogpage(5, logpage_buf).waitdone()
        return logpage_buf.data((opcode+1)*4-1, opcode*4) != 0

    def waitdone(self, expected=1):
        """sync until expected commands completion

        Notice
            Do not call this function in commands callback functions.

        # Parameters
            expected (int): expected commands to complete. Default: 1
        """

        reaped = 0

        global _reentry_flag
        assert _reentry_flag is False, "cannot re-entry waitdone() functions which may be caused by waitdone in callback functions, %d" % _reentry_flag
        _reentry_flag = True

        logging.debug("to reap %d admin commands" % expected)
        # some admin commands need long timeout limit, like: format,
        signal.alarm(self._timeout_pynvme)

        while reaped < expected:
            # wait admin Q pair done
            reaped += d.nvme_wait_completion_admin(self._ctrlr)

            # Since signals are delivered asynchronously at unpredictable
            # times, it is problematic to run any meaningful code directly
            # from the signal handler. Therefore, Python queues incoming
            # signals. The queue is processed later as part of the interpreter
            # loop. If your code is fully compiled, interpreter loop is never
            # executed and Python has no chance to check and run queued signal
            # handlers.
            # - from: https://stackoverflow.com/questions/16769870/cython-python-and-keyboardinterrupt-ignored
            PyErr_CheckSignals()
        signal.alarm(0)

        # in admin queue, may reap more than expected, because driver
        # will get admin CQ as many as possible
        assert reaped >= expected, \
            "not reap the exact completions! reaped %d, expected %d" % (reaped, expected)
        _reentry_flag = False

    def abort(self, cid, sqid=0, cb=None):
        """abort admin commands

        # Parameters
            cid (int): command id of the command to be aborted
            sqid (int): sq id of the command to be aborted. Default: 0, to abort the admin command
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        self.send_admin_raw(None, 0x8,
                            nsid=0,
                            cdw10=(cid<<16)+sqid,
                            cdw11=0,
                            cdw12=0,
                            cdw13=0,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def identify(self, buf, nsid=0, cns=1, cb=None):
        """identify admin command

        # Parameters
            buf (Buffer): the buffer to hold the identify data
            nsid (int): nsid field in the command. Default: 0
            cns (int): cns field in the command. Default: 1
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        self.send_admin_raw(buf, 0x6,
                            nsid=nsid,
                            cdw10=cns,
                            cdw11=0,
                            cdw12=0,
                            cdw13=0,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def id_data(self, byte_end, byte_begin=None, type=int, nsid=0, cns=1):
        """get field in controller identify data

        # Parameters
            byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.
            byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
            type (type): the type of the field. It should be int or str. Default: int, convert to integer python object

        # Returns
            (int or str): the data in the specified field
        """

        id_buf = Buffer(4096)
        self.identify(id_buf, nsid, cns).waitdone()
        return id_buf.data(byte_end, byte_begin, type)

    def getfeatures(self, fid, cdw11=0, cdw12=0, cdw13=0, cdw14=0, cdw15=0,
                    sel=0, buf=None, cb=None):
        """getfeatures admin command

        # Parameters
            fid (int): feature id
            cdw11 (int): cdw11 in the command. Default: 0
            sel (int): sel field in the command. Default: 0
            buf (Buffer): the buffer to hold the feature data. Default: None
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """
        self.send_admin_raw(buf, 0xA,
                            nsid=1,
                            cdw10=(sel << 8)+fid,
                            cdw11=cdw11,
                            cdw12=cdw12,
                            cdw13=cdw13,
                            cdw14=cdw14,
                            cdw15=cdw15,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def setfeatures(self, fid, cdw11=0, cdw12=0, cdw13=0, cdw14=0, cdw15=0,
                    sv=0, buf=None, cb=None):
        """setfeatures admin command

        # Parameters
            fid (int): feature id
            cdw11 (int): cdw11 in the command. Default: 0
            sv (int): sv field in the command. Default: 0
            buf (Buffer): the buffer to hold the feature data. Default: None
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        self.send_admin_raw(buf, 0x9,
                            nsid=0xffffffff,
                            cdw10=(sv << 31)+fid,
                            cdw11=cdw11,
                            cdw12=cdw12,
                            cdw13=cdw13,
                            cdw14=cdw14,
                            cdw15=cdw15,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def getlogpage(self, lid, buf, size=None, offset=0, nsid=0xffffffff, cb=None):
        """getlogpage admin command

        # Parameters
            lid (int): Log Page Identifier
            buf (Buffer): buffer to hold the log page
            size (int): size (in byte) of data to get from the log page,. Default: None, means the size is the same of the buffer
            offset (int): the location within a log page
            nsid (int): nsid field in the command. Default: 0xffffffff
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        if size is None:  size = len(buf)  # the same size of buffer
        assert size%4 == 0, "size must be dword aligned"
        assert offset%4 == 0, "offset must be dword aligned"

        dwords = (size >> 2) - 1  # zero-based dword number
        assert dwords >= 0
        assert dwords < 0x1_0000_0000, "32-bit field"
        assert offset >= 0
        assert offset < 0x1_0000_0000_0000_0000, "64-bit field"

        self.send_admin_raw(buf, 0x2,
                            nsid=nsid,
                            cdw10=((dwords & 0xffff) << 16) + lid,
                            cdw11=dwords >> 16,
                            cdw12=offset,
                            cdw13=offset >> 32,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def format(self, lbaf=0, ses=0, nsid=1, cb=None):
        """format admin command

        Notice
            This Controller.format only send the admin command. Use Namespace.format to maintain pynvme internal data!

        # Parameters
            lbaf (int): lbaf (lba format) field in the command. Default: 0
            ses (int): ses field in the command. Default: 0, no secure erase
            nsid (int): nsid field in the command. Default: 1
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        assert ses < 8, "invalid format ses"
        assert lbaf < 16, "invalid format lbaf"

        self.send_admin_raw(None, 0x80,
                            nsid=nsid,
                            cdw10=(ses<<9) + lbaf,
                            cdw11=0,
                            cdw12=0,
                            cdw13=0,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)

        return self

    def sanitize(self, option=2, pattern=0, cb=None):
        """sanitize admin command

        # Parameters
            option (int): sanitize option field in the command
            pattern (int): pattern field in the command for overwrite method. Default: 0x5aa5a55a
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        # clear crc table of all namespaces
        for nsid in range(1, self.id_data(519, 516)+1):
            ns = d.nvme_get_ns(self._ctrlr, nsid)
            d.ns_crc32_clear(ns, 0, 0, True, False)

        self.send_admin_raw(None, 0x84,
                            nsid=0,
                            cdw10=option,
                            cdw11=pattern,
                            cdw12=0,
                            cdw13=0,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def dst(self, stc=1, nsid=0xffffffff, cb=None):
        """device self test (DST) admin command

        # Parameters
            stc (int): selftest code (stc) field in the command
            nsid (int): nsid field in the command. Default: 0xffffffff
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        self.send_admin_raw(None, 0x14,
                            nsid=nsid,
                            cdw10=stc,
                            cdw11=0,
                            cdw12=0,
                            cdw13=0,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def fw_download(self, buf, offset, size=None, cb=None):
        """firmware download admin command

        # Parameters
            buf (Buffer): the buffer to hold the firmware data
            offset (int): offset field in the command
            size (int): size field in the command. Default: None, means the size of the buffer
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        if size is None:  size = len(buf)  # the same size of buffer
        logging.debug("firmware image download, offset 0x%x, size %d" % (offset, size))
        self.send_admin_raw(buf, 0x11,
                            nsid=0,
                            cdw10=(size>>2)-1,  # zero-based dword number
                            cdw11=(offset>>2),  # unit is dword
                            cdw12=0,
                            cdw13=0,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def fw_commit(self, slot, action, cb=None):
        """firmware commit admin command

        # Parameters
            slot (int): firmware slot field in the command
            action (int): action field in the command
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        # no need to block invalid test parameters for DUT
        assert slot < 8, "invalid fw slot: %d" % slot
        assert action < 8, "invalid fw commit action: %d" % action

        logging.debug("firmware commit, slot %d, action %d" % (slot, action))
        self.send_admin_raw(None, 0x10,
                            nsid=0,
                            cdw10=(action<<3)+slot,
                            cdw11=0,
                            cdw12=0,
                            cdw13=0,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def downfw(self, filename, slot=0, action=1):
        """firmware download utility: by 4K, and activate in next reset

        # Parameters
            filename (str): the pathname of the firmware binary file to download
            slot (int): firmware slot field in the command. Default: 0, decided by device
            cb (function): callback function called at completion. Default: None

        # Returns
        """

        logging.info("download firmware image %s to slot %d and activate" % (filename, slot))
        with open(filename, "rb") as f:
            buf = Buffer(4096)
            for i, chunk in enumerate(iter(lambda: f.read(4096), b'')):
                buf[:] = chunk
                self.fw_download(buf, 4096*i).waitdone()
        self.fw_commit(slot, action).waitdone()
        logging.info("download firmware completed")

    def aer(self, cb=None):
        """asynchorous event request admin command.

        Not suggested to use this command in scripts because driver manages to send and monitor aer commands. Scripts should register an aer callback function if it wants to handle aer, and use the fixture aer.

        # Parameters
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        self.send_admin_raw(None, 0xc,
                            nsid=0,
                            cdw10=0,
                            cdw11=0,
                            cdw12=0,
                            cdw13=0,
                            cdw14=0,
                            cdw15=0,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    def register_aer_cb(self, func):
        """register aer callback to driver.

        It is recommended to use fixture aer(func) in pytest scripts.
        When aer is triggered, the python callback function will
        be called. It is unregistered by aer fixture when test finish.

        # Parameters
            func (function): callback function called at aer completion
        """

        d.nvme_register_aer_cb(self._ctrlr, aer_cmd_cb, <void*>func)

    def send_cmd(self, opcode, buf=None, nsid=0,
                 cdw10=0, cdw11=0, cdw12=0,
                 cdw13=0, cdw14=0, cdw15=0,
                 cb=None):
        """send generic admin commands.

        This is a generic method. Scripts can use this method to send all kinds of commands, like Vendor Specific commands, and even not existed commands.

        # Parameters
            opcode (int): operate code of the command
            buf (Buffer): buffer of the command. Default: None
            nsid (int): nsid field of the command. Default: 0
            cb (function): callback function called at completion. Default: None

        # Returns
            self (Controller)
        """

        self.send_admin_raw(buf, opcode,
                            nsid,
                            cdw10,
                            cdw11,
                            cdw12,
                            cdw13,
                            cdw14,
                            cdw15,
                            cb_func=cmd_cb,
                            cb_arg=<void*>cb)
        return self

    cdef int send_admin_raw(self,
                            Buffer buf,
                            unsigned int opcode,
                            unsigned int nsid,
                            unsigned int cdw10,
                            unsigned int cdw11,
                            unsigned int cdw12,
                            unsigned int cdw13,
                            unsigned int cdw14,
                            unsigned int cdw15,
                            d.cmd_cb_func cb_func,
                            void* cb_arg):
        cdef void* ptr
        cdef size_t size

        if buf is None:
            ptr = NULL
            size = 0
        else:
            ptr = buf.ptr
            size = buf.size

        logging.debug("send admin command, opcode %xh" % opcode)
        ret = d.nvme_send_cmd_raw(self._ctrlr, NULL, opcode, nsid, ptr, size,
                                  cdw10, cdw11, cdw12, cdw13, cdw14, cdw15,
                                  cb_func, cb_arg)
        assert ret == 0, "error in submitting admin commands, 0x%x" % ret
        return ret


class QpairCreationError(Exception):
    pass


class QpairDeletionError(Exception):
    pass


cdef class Qpair(object):
    """Qpair class. IO SQ and CQ are combinded as qpairs.

    # Parameters
        nvme (Controller): controller where to create the queue
        depth (int): SQ/CQ queue depth
        prio (int): when Weighted Round Robin is enabled, specify SQ priority here
    """

    cdef d.qpair * _qpair
    cdef Controller _nvme

    def __cinit__(self, Controller nvme,
                  unsigned int depth,
                  unsigned int prio=0):
        # create CQ and SQ
        if depth < 2:
            raise QpairCreationError("depth should >= 2")

        self._qpair = d.qpair_create(nvme._ctrlr, prio, depth)
        if self._qpair is NULL:
            raise QpairCreationError("qpair create fail")
        self._nvme = nvme

    def __dealloc__(self):
        # print("dealloc qpair: %x" % <unsigned long>self._qpair); sys.stdout.flush()
        if self._qpair is not NULL and self._nvme._ctrlr is not NULL:
            if d.qpair_free(self._qpair) != 0:
                raise QpairDeletionError()
            self._qpair = NULL

    def __repr__(self):
        return "<qpair: %d>" % self.sqid

    @property
    def sqid(self):
        return d.qpair_get_id(self._qpair)

    def cmdlog(self, count=0):
        """print recent IO commands and their completions in this qpair.

        # Parameters
            count (int): the number of commands to print. Default: 0, to print the whole cmdlog
        """

        d.log_cmd_dump(self._qpair, count)

    def msix_clear(self):
        d.intc_clear(self._qpair)

    def msix_isset(self):
        return d.intc_isset(self._qpair)

    def msix_mask(self):
        d.intc_mask(self._qpair)

    def msix_unmask(self):
        d.intc_unmask(self._qpair)

    def waitdone(self, expected=1):
        """sync until expected commands completion

        Notice
            Do not call this function in commands callback functions.

        # Parameters
            expected (int): expected commands to complete. Default: 1
        """

        reaped = 0

        global _reentry_flag
        assert _reentry_flag is False, "cannot re-entry waitdone() functions which may be caused by waitdone in callback functions, %d" % _reentry_flag
        _reentry_flag = True

        logging.debug("to reap %d io commands, sqid %d" % (expected, self.sqid))
        signal.alarm(self._nvme._timeout_pynvme)

        while reaped < expected:
            # wait IO Q pair done, max 8 cpl in one time
            max_to_reap = (expected-reaped) % 8
            reaped += d.qpair_wait_completion(self._qpair, max_to_reap)
            PyErr_CheckSignals()
        signal.alarm(0)

        assert reaped == expected, \
            "not reap the exact completions! reaped %d, expected %d" % (reaped, expected)
        _reentry_flag = False


class NamespaceCreationError(Exception):
    pass


class NamespaceDeletionError(Exception):
    pass


cdef class Namespace(object):
    """Namespace class. Prefer to use fixture "nvme0n1" in test scripts.

    # Parameters
        nvme (Controller): controller where to create the queue
        nsid (int): nsid of the namespace
    """

    cdef d.namespace * _ns
    cdef unsigned int _nsid
    cdef unsigned int sector_size
    cdef Controller _nvme

    def __cinit__(self, Controller nvme, unsigned int nsid=1):
        logging.debug("initialize namespace nsid %d" % nsid)
        self._nvme = nvme
        self._nsid = nsid
        self._ns = d.ns_init(nvme._ctrlr, nsid)
        #print("created namespace: 0x%x" % <unsigned long>self._ns); sys.stdout.flush()
        if self._ns is NULL:
            raise NamespaceCreationError()
        self.sector_size = d.ns_get_sector_size(self._ns)

    def close(self):
        """close namespace to release it resources in host memory.

        Notice
            Release resources explictly, del is not garentee to call __dealloc__.
            Fixture nvme0n1 uses this function, and prefer to use fixture in scripts, instead of calling this function directly.
        """

        logging.debug("close namespace")
        #print("dealloc namespace: 0x%x" % <unsigned long>self._ns); sys.stdout.flush()
        self._ns = d.nvme_get_ns(self._nvme._ctrlr, self._nsid)
        if self._ns is not NULL:
            if d.ns_fini(self._ns) != 0:
                raise NamespaceDeletionError()
            self._ns = NULL

    @property
    def nsid(self):
        """id of the namespace"""
        return self._nsid

    @property
    def capacity(self):
        """bytes of namespace capacity"""
        return self.id_data(63, 48)

    def cmdname(self, opcode):
        """get the name of the IO command

        # Parameters
            opcode (int): the opcode of the IO command

        # Returns
            (str): the command name
        """

        assert opcode < 256
        name = d.cmd_name(opcode, 1)
        return name.decode('ascii')

    def supports(self, opcode):
        """check if the IO command is supported

        # Parameters
            opcode (int): the opcode of the IO command

        # Returns
            (bool): if the command is supported
        """

        assert opcode < 256
        return self._nvme.supports(256+opcode)

    def id_data(self, byte_end, byte_begin=None, type=int):
        """get field in namespace identify data

        # Parameters
            byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.
            byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
            type (type): the type of the field. It should be int or str. Default: int, convert to integer python object

        # Returns
            (int or str): the data in the specified field
        """

        return self._nvme.id_data(byte_end, byte_begin, type, self._nsid, 0)

    def format(self, data_size=512, meta_size=0, ses=0):
        """change the format of this namespace

        Notice
            this facility not only sends format admin command, but also updates driver to activate new format immediately

        # Parameters
            data_size (int): data size. Default: 512
            meta_size (int): meta data size. Default: 0
            ses (int): ses field in the command. Default: 0, no secure erase

        # Returns
            (int or None): the lba format has the specified data size and meta data size
        """

        lbaf = self.get_lba_format(data_size, meta_size)
        self._nvme.format(lbaf, ses, self._nsid).waitdone()
        self._ns = d.nvme_get_ns(self._nvme._ctrlr, self._nsid)
        d.ns_refresh(self._ns, self._nsid, self._nvme._ctrlr)

        # clear crc table
        logging.debug("clear crc table")
        d.ns_crc32_clear(self._ns, 0, 0, True, False)


    def get_lba_format(self, data_size=512, meta_size=0):
        """find the lba format by its data size and meta data size

        # Parameters
            data_size (int): data size. Default: 512
            meta_size (int): meta data size. Default: 0

        # Returns
            (int or None): the lba format has the specified data size and meta data size
        """

        for fid in range(16):
            format_support = self.id_data(128+fid*4+3, 128+fid*4)
            if data_size == (1<<((format_support>>16)&0xff)) and \
               meta_size == (format_support&0xffff):
                return fid

    def ioworker(self, io_size, lba_align=None, lba_random=True,
                 read_percentage=100, time=0, qdepth=64,
                 region_start=0, region_end=0xffff_ffff_ffff_ffff,
                 iops=0, io_count=0, lba_start=0, qprio=0,
                 distribution=None, pvalue=0, ptype=0,
                 output_io_per_second=None,
                 output_percentile_latency=None):
        """workers sending different read/write IO on different CPU cores.

        User defines IO characteristics in parameters, and then the ioworker
        executes without user intervesion, until the test is completed. IOWorker
        returns some statistic data at last.

        User can start multiple IOWorkers, and they will be binded to different
        CPU cores. Each IOWorker creates its own Qpair, so active IOWorker counts
        is limited by maximum IO queues that DUT can provide.

        Each ioworker can run upto 24 hours.

        # Parameters
            io_size (short, range, list, dict): IO size, unit is LBA. It can be a fixed size, or a range or list of size, or specify ratio in the dict if they are not evenly distributed
            lba_align (short): IO alignment, unit is LBA. Default: None: same as io_size when it < 4K, or it is 4K
            lba_random (bool): True if sending IO with random starting LBA. Default: True
            read_percentage (int): sending read/write mixed IO, 0 means write only, 100 means read only. Default: 100
            time (int): specified maximum time of the IOWorker in seconds, up to 1000*3600. Default:0, means no limit
            qdepth (int): queue depth of the Qpair created by the IOWorker, up to 1024. Default: 64
            region_start (long): sending IO in the specified LBA region, start. Default: 0
            region_end (long): sending IO in the specified LBA region, end but not include. Default: 0xffff_ffff_ffff_ffff
            iops (int): specified maximum IOPS. IOWorker throttles the sending IO speed. Default: 0, means no limit
            io_count (long): specified maximum IO counts to send. Default: 0, means no limit
            lba_start (long): the LBA address of the first command. Default: 0, means start from region_start
            qprio (int): SQ priority. Default: 0, as Round Robin arbitration
            distribution (list(int)): distribute 10,000 IO to 100 sections. Default: None
            pvalue (int): data pattern value. Refer to data pattern in class `Buffer`. Default: 0
            ptype (int): data pattern type. Refer to data pattern in class `Buffer`. Default: 0
            output_io_per_second (list): list to hold the output data of io_per_second. Default: None, not to collect the data
            output_percentile_latency (dict): dict of io counter on different percentile latency. Dict key is the percentage, and the value is the latency in micro-second. Default: None, not to collect the data

        # Returns
            ioworker object
        """

        assert not (time==0 and io_count==0), "when to stop the ioworker?"
        assert qdepth>=2 and qdepth<=1023, "support qdepth upto 1023"
        assert qdepth <= (self._nvme.cap & 0xffff) + 1, "qdepth is larger than specification"
        assert region_start < region_end, "region end is not included"
        assert io_count != 0 or time != 0, "worker needs a rest :)"
        assert time <= 1000*3600ULL, "worker needs a rest :)"

        # convert any possible io_size input to dict
        if isinstance(io_size, int):
            io_size = [io_size, ]
        if isinstance(io_size, range):
            io_size = list(io_size)
        if isinstance(io_size, list):
            io_size = {i : 1 for i in io_size}
        assert isinstance(io_size, dict)
        assert 0 not in io_size.keys(), "io_size cannot be 0"

        # set default alignment if it is specified
        if not lba_align:
            lba_align = [min(s, 8) for s in io_size.keys()]
        if isinstance(lba_align, int):
            lba_align = [lba_align, ]
        assert isinstance(lba_align, list)
        assert 0 not in lba_align, "lba_align cannot be 0"

        pciaddr = self._nvme._bdf
        nsid = self._nsid
        return _IOWorker(pciaddr, nsid, lba_start, io_size, lba_align,
                         lba_random, region_start, region_end,
                         read_percentage, iops, io_count, time, qdepth, qprio,
                         distribution, pvalue, ptype,
                         output_io_per_second, output_percentile_latency)

    def read(self, qpair, buf, lba, lba_count=1, io_flags=0, cb=None):
        """read IO command

        Notice
            buf cannot be released before the command completes.

        # Parameters
            qpair (Qpair): use the qpair to send this command
            buf (Buffer): the data buffer of the command, meta data is not supported.
            lba (int): the starting lba address, 64 bits
            lba_count (int): the lba count of this command, 16 bits. Default: 1
            io_flags (int): io flags defined in NVMe specification, 16 bits. Default: 0
            cb (function): callback function called at completion. Default: None

        # Returns
            qpair (Qpair): the qpair used to send this command, for ease of chained call

        # Raises
            SystemError: the read command fails
        """

        assert buf is not None, "no buffer allocated"
        if 0 != self.send_read_write(True, qpair, buf, lba, lba_count,
                                     io_flags, cmd_cb, <void*>cb):
            raise SystemError()
        return qpair

    def write(self, qpair, buf, lba, lba_count=1, io_flags=0, cb=None):
        """write IO command

        Notice
            buf cannot be released before the command completes.

        # Parameters
            qpair (Qpair): use the qpair to send this command
            buf (Buffer): the data buffer of the write command, meta data is not supported.
            lba (int): the starting lba address, 64 bits
            lba_count (int): the lba count of this command, 16 bits
            io_flags (int): io flags defined in NVMe specification, 16 bits. Default: 0
            cb (function): callback function called at completion. Default: None

        # Returns
            qpair (Qpair): the qpair used to send this command, for ease of chained call

        # Raises
            SystemError: the write command fails
        """

        assert buf is not None, "no buffer allocated"

        if 0 != self.send_read_write(False, qpair, buf, lba, lba_count,
                                     io_flags, cmd_cb, <void*>cb):
            raise SystemError()

        return qpair

    def dsm(self, qpair, buf, range_count, attribute=0x4, cb=None):
        """data-set management IO command

        Notice
            buf cannot be released before the command completes.

        # Parameters
            qpair (Qpair): use the qpair to send this command
            buf (Buffer): the buffer of the lba ranges. Use buffer.set_dsm_range to prepare the buffer.
            range_count (int): the count of lba ranges in the buffer
            attribute (int): attribute field of the command. Default: 0x4, as deallocation/trim
            cb (function): callback function called at completion. Default: None

        # Returns
            qpair (Qpair): the qpair used to send this command, for ease of chained call

        # Raises
            SystemError: the command fails
        """

        assert buf is not None, "no range prepared"

        # update host-side table for the trimed data
        self.deallocate_ranges(buf, range_count)

        # send the command
        self.send_io_raw(qpair, buf, 9, self._nsid,
                         range_count-1, attribute,
                         0, 0, 0, 0,
                         cmd_cb, <void*>cb)
        return qpair

    def compare(self, qpair, buf, lba, lba_count=1, io_flags=0, cb=None):
        """compare IO command

        Notice
            buf cannot be released before the command completes.

        # Parameters
            qpair (Qpair): use the qpair to send this command
            buf (Buffer): the data buffer of the command, meta data is not supported.
            lba (int): the starting lba address, 64 bits
            lba_count (int): the lba count of this command, 16 bits. Default: 1
            io_flags (int): io flags defined in NVMe specification, 16 bits. Default: 0
            cb (function): callback function called at completion. Default: None

        # Returns
            qpair (Qpair): the qpair used to send this command, for ease of chained call

        # Raises
            SystemError: the command fails
        """

        assert buf is not None, "no buffer allocated"

        self.send_io_raw(qpair, buf, 5, self._nsid,
                         lba, lba>>32,
                         (lba_count-1)+(io_flags<<16),
                         0, 0, 0,
                         cmd_cb, <void*>cb)
        return qpair

    def flush(self, qpair, cb=None):
        """flush IO command

        # Parameters
            qpair (Qpair): use the qpair to send this command
            cb (function): callback function called at completion. Default: None

        # Returns
            qpair (Qpair): the qpair used to send this command, for ease of chained call

        # Raises
            SystemError: the command fails
        """

        self.send_io_raw(qpair, None, 0, self._nsid,
                         0, 0, 0, 0, 0, 0,
                         cmd_cb, <void*>cb)
        return qpair

    def write_uncorrectable(self, qpair, lba, lba_count=1, cb=None):
        """write uncorrectable IO command

        # Parameters
            qpair (Qpair): use the qpair to send this command
            lba (int): the starting lba address, 64 bits
            lba_count (int): the lba count of this command, 16 bits. Default: 1
            cb (function): callback function called at completion. Default: None

        # Returns
            qpair (Qpair): the qpair used to send this command, for ease of chained call

        # Raises
            SystemError: the command fails
        """

        self._ns = d.nvme_get_ns(self._nvme._ctrlr, self._nsid)
        d.ns_crc32_clear(self._ns, lba, lba_count, False, True)
        self.send_io_raw(qpair, None, 4, self._nsid,
                         lba, lba>>32,
                         lba_count-1,
                         0, 0, 0,
                         cmd_cb, <void*>cb)
        return qpair

    def write_zeroes(self, qpair, lba, lba_count=1, io_flags=0, cb=None):
        """write zeroes IO command

        # Parameters
            qpair (Qpair): use the qpair to send this command
            lba (int): the starting lba address, 64 bits
            lba_count (int): the lba count of this command, 16 bits. Default: 1
            io_flags (int): io flags defined in NVMe specification, 16 bits. Default: 0
            cb (function): callback function called at completion. Default: None

        # Returns
            qpair (Qpair): the qpair used to send this command, for ease of chained call

        # Raises
            SystemError: the command fails
        """

        self._ns = d.nvme_get_ns(self._nvme._ctrlr, self._nsid)
        d.ns_crc32_clear(self._ns, lba, lba_count, False, False)
        self.send_io_raw(qpair, None, 8, self._nsid,
                         lba, lba>>32,
                         (lba_count-1)+(io_flags<<16),
                         0, 0, 0,
                         cmd_cb, <void*>cb)
        return qpair

    cdef int send_read_write(self,
                             bint is_read,
                             Qpair qpair,
                             Buffer buf,
                             unsigned long lba,
                             unsigned short lba_count,
                             unsigned int io_flags,
                             d.cmd_cb_func cb_func,
                             void* cb_arg):
        self._ns = d.nvme_get_ns(self._nvme._ctrlr, self._nsid)
        ret = d.ns_cmd_read_write(is_read, self._ns, qpair._qpair,
                                  buf.ptr, buf.size,
                                  lba, lba_count, io_flags,
                                  cb_func, cb_arg)
        assert ret == 0, "error in submitting read write commands: 0x%x" % ret
        return ret

    def send_cmd(self, opcode, qpair, buf=None, nsid=0,
                 cdw10=0, cdw11=0, cdw12=0,
                 cdw13=0, cdw14=0, cdw15=0,
                 cb=None):
        """send generic IO commands.

        This is a generic method. Scripts can use this method to send all kinds of commands, like Vendor Specific commands, and even not existed commands.

        # Parameters
            opcode (int): operate code of the command
            qpair (Qpair): qpair used to send this command
            buf (Buffer): buffer of the command. Default: None
            nsid (int): nsid field of the command. Default: 0
            cb (function): callback function called at completion. Default: None

        # Returns
            qpair (Qpair): the qpair used to send this command, for ease of chained call
        """

        self.send_io_raw(qpair, buf, opcode,
                         nsid,
                         cdw10,
                         cdw11,
                         cdw12,
                         cdw13,
                         cdw14,
                         cdw15,
                         cb_func=cmd_cb,
                         cb_arg=<void*>cb)
        return qpair

    cdef void deallocate_ranges(self,
                                Buffer buf,
                                unsigned int range_count):
        self._ns = d.nvme_get_ns(self._nvme._ctrlr, self._nsid)
        d.nvme_deallocate_ranges(self._ns, buf.ptr, range_count)

    cdef int send_io_raw(self,
                         Qpair qpair,
                         Buffer buf,
                         unsigned int opcode,
                         unsigned int nsid,
                         unsigned int cdw10,
                         unsigned int cdw11,
                         unsigned int cdw12,
                         unsigned int cdw13,
                         unsigned int cdw14,
                         unsigned int cdw15,
                         d.cmd_cb_func cb_func,
                         void* cb_arg):
        if buf is None:
            ptr = NULL
            size = 0
        else:
            ptr = buf.ptr
            size = buf.size

        ret = d.nvme_send_cmd_raw(self._nvme._ctrlr, qpair._qpair, opcode,
                                  nsid, ptr, size, cdw10, cdw11, cdw12,
                                  cdw13, cdw14, cdw15, cb_func, cb_arg)
        assert ret == 0, "error in submitting io commands, 0x%x" % ret
        return ret


class DotDict(dict):
    """utility class to access dict members by . operation"""
    def __init__(self, *args, **kwargs):
        super(DotDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class _IOWorker(object):
    """A process-worker executing user functions. Use its wrapper function Namespace.ioworker() in scripts. """

    target_start_time = 0

    def __init__(self, pciaddr, nsid, lba_start, lba_size, lba_align,
                 lba_random, region_start, region_end,
                 read_percentage, iops, io_count, time, qdepth, qprio,
                 distribution, pvalue, ptype,
                 output_io_per_second, output_percentile_latency):
        # queue for returning result
        self.q = _mp.Queue()

        # lock for processes sync
        self.l = _mp.Lock()

        # create the child process
        self.p = _mp.Process(target = self._ioworker,
                             args = (self.q, self.l, pciaddr, nsid, _random_seed,
                                     lba_start, lba_size, lba_align, lba_random,
                                     region_start, region_end, read_percentage,
                                     iops, io_count, time, qdepth, qprio,
                                     distribution, pvalue, ptype,
                                     output_io_per_second, output_percentile_latency))
        self.output_io_per_second = output_io_per_second
        self.output_percentile_latency = output_percentile_latency
        self.p.daemon = True

    def start(self):
        """Start the worker's process"""
        self.p.start()
        return self

    def find_percentile_latency(self, k, output_io_per_latency):
        target = sum(output_io_per_latency) * k // 100
        total = 0
        for l, c in enumerate(output_io_per_latency):
            total += c
            if total >= target:
                return l
        assert False, "should find the latency in the loop"

    def close(self):
        """Wait the worker's process finish

        Wait the worker process complete, and get the return report data
        """

        # get data from queue before joinging the subprocess, otherwise deadlock
        childpid, error, rets, output_io_per_second, output_io_per_latency = self.q.get()
        rets = DotDict(rets)
        self.p.join()

        if error != 0:
            warnings.warn("ioworker host ERROR %d" % error)

        if rets.error != 0:
            warnings.warn("ioworker device ERROR status: %02x/%02x" %
                          ((rets.error>>8)&0x7, rets.error&0xff))

        # transfer output table back: driver => script
        if self.output_io_per_second is not None:
            assert len(self.output_io_per_second) == 0
            self.output_io_per_second += output_io_per_second[:rets['mseconds']//1000]
            rets['iops_consistency'] = self.iops_consistency()

        # transfer output table back: driver => script
        if output_io_per_latency is not None:
            # latency average
            latency_sum = 0
            for us, num in enumerate(output_io_per_latency):
                latency_sum += us*num
            rets['latency_average_us'] = latency_sum//sum(output_io_per_latency)

            # distribution, group to 100 groups
            end99 = self.find_percentile_latency(99, output_io_per_latency)
            unit = (end99+99)//100
            output_io_per_latency_grouped = []
            for i in range(0, unit*100, unit):
                output_io_per_latency_grouped.append(sum(output_io_per_latency[i:i+unit]))
            rets['latency_distribution_grouped_unit_us'] = unit
            rets['latency_distribution_grouped'] = output_io_per_latency_grouped

            # calculate percentile latencies
            for i, k in enumerate(self.output_percentile_latency):
                assert k>0 and k<100, "percentile should be in (0, 100)"
                self.output_percentile_latency[k] = self.find_percentile_latency(k, output_io_per_latency)

        # release child process resources
        del self.q
        for f in glob.glob("/var/run/dpdk/spdk0/fbarray_memseg*%d" % childpid):
            os.remove(f)

        return rets

    def iops_consistency(self, slowest_percentage=99.9):
        assert self.output_io_per_second is not None, "iops consistency data is not collected"
        assert slowest_percentage > 0, "the percentage must be larger than 0"
        assert slowest_percentage < 100, "the percentage must be smaller than 100"
        assert self.output_io_per_second, "output list is empty"
        average = sum(self.output_io_per_second)/len(self.output_io_per_second)
        index = int(len(self.output_io_per_second)*slowest_percentage)//100
        return sorted(self.output_io_per_second, reverse=True)[index]/average

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert exc_value is None, "ioworker exits with exception: %s" % exc_value
        self.close()
        return True

    def _ioworker(self, rqueue, locker, pciaddr, nsid, seed,
                  lba_start, lba_size, lba_align, lba_random,
                  region_start, region_end, read_percentage,
                  iops, io_count, seconds, qdepth, qprio,
                  distribution, pvalue, ptype,
                  output_io_per_second, output_percentile_latency):
        cdef d.ioworker_args args
        cdef d.ioworker_rets rets
        cdef int error = 0
        output_io_per_latency = None

        try:
            # register events in worker's processor
            # CTRL-c to exit
            signal.signal(signal.SIGINT, _interrupt_handler)
            # timeout
            signal.signal(signal.SIGALRM, _timeout_signal_handler)

            # setup random seed
            d.driver_srand(seed)
            random.seed(seed)

            # init var
            _reentry_flag_init()
            memset(&args, 0, sizeof(args))
            memset(&rets, 0, sizeof(rets))

            # setup lba_size lists
            assert isinstance(lba_size, dict)
            assert isinstance(lba_align, list)
            assert len(lba_size) == len(lba_align), "size and align not match"
            args.lba_size_max = max(lba_size.keys())
            args.lba_align_max = max(lba_align)
            args.lba_size_ratio_sum = sum(lba_size[i] for i in lba_size)
            assert args.lba_size_ratio_sum <= 10000, "please simplify the io_size ratios"
            args.lba_size_list = <unsigned int*>PyMem_Malloc(len(lba_size)*sizeof(unsigned int))
            args.lba_size_list_len = len(lba_size)
            args.lba_size_list_ratio = <unsigned int*>PyMem_Malloc(len(lba_size)*sizeof(unsigned int))
            args.lba_size_list_align = <unsigned int*>PyMem_Malloc(len(lba_size)*sizeof(unsigned int))
            for i, io_size in enumerate(lba_size):
                args.lba_size_list[i] = io_size
                args.lba_size_list_ratio[i] = lba_size[io_size]
                args.lba_size_list_align[i] = lba_align[i]
                assert io_size < 0x10000, "io_size is a 16bit-field in commands"
                assert lba_align[i] < 0x10000, "io_size is a 16bit-field in commands"

            # check distribution
            if distribution is not None:
                assert region_start == 0, "distribution has to be on the full region"
                assert region_end == 0xffff_ffff_ffff_ffff, "distribution has to be on the full region"
                assert len(distribution) == 100, "distribution on 100 equal sections"
                assert sum(distribution) == 10000, "distribute 10000 IO on 100 sections"
                assert lba_random == True, "distribution has to be random IO"
                args.distribution = <unsigned int*>PyMem_Malloc(100*sizeof(unsigned int))
                for i in range(100):
                    args.distribution[i] = distribution[i]

            if seconds == 0:
                # collect upto 1000hr IOPS data
                seconds = 1000*3600ULL
                
            # create array for output data: io counter per second
            if output_io_per_second is not None:
                # need time duration to collect io counter per second data
                args.io_counter_per_second = <unsigned int*>PyMem_Malloc(seconds*sizeof(unsigned int))
                memset(args.io_counter_per_second, 0, seconds*sizeof(unsigned int))

            # create array for output data: io counter per latency
            if output_percentile_latency is not None:
                # 1-1000,000 us, all latency > 1s are counted as 1000,000us
                args.io_counter_per_latency = <unsigned int*>PyMem_Malloc(1000*1000*sizeof(unsigned int))

            # transfer agurments
            args.lba_start = lba_start
            args.lba_random = lba_random
            args.region_start = region_start
            args.region_end = region_end
            args.read_percentage = read_percentage
            args.iops = iops
            args.io_count = io_count
            args.seconds = seconds
            args.qdepth = qdepth
            args.pvalue = pvalue
            args.ptype = ptype

            # ready: create resources
            with locker:
                nvme0 = Controller(pciaddr)
                nvme0n1 = Namespace(nvme0, nsid)
                qpair = Qpair(nvme0, max(2, qdepth), qprio)

            # set: all ioworkers created in recent seconds will start at the same time
            if time.time() > _IOWorker.target_start_time:
                _IOWorker.target_start_time = math.ceil(time.time())+1
            time.sleep(_IOWorker.target_start_time-time.time())

            # go: start at the same time
            error = d.ioworker_entry(nvme0n1._ns, qpair._qpair, &args, &rets)

            # transfer back iops counter per second: c => cython
            if output_io_per_second is not None:
                for i in range(seconds):
                    output_io_per_second.append(args.io_counter_per_second[i])

            # transfer back percentile latency: c => cython
            if output_percentile_latency is not None:
                output_io_per_latency = []
                for i in range(1000*1000):
                    output_io_per_latency.append(args.io_counter_per_latency[i])

        except Exception as e:
            logging.warning(e)
            warnings.warn(e)
            error = -1

        finally:
            # checkout timeout event
            if _timeout_happened:
                error = -10

            # feed return to main process
            rqueue.put((os.getpid(),
                        error,
                        rets,
                        output_io_per_second,
                        output_io_per_latency))

            with locker:
                # close resources in right order
                if 'nvme0n1' in locals():
                    nvme0n1.close()

                # delete resources
                if 'qpair' in locals():
                    del qpair

                if 'nvme0n1' in locals():
                    del nvme0n1

                if 'nvme0' in locals():
                    del nvme0

            if args.io_counter_per_second:
                PyMem_Free(args.io_counter_per_second)

            if args.io_counter_per_latency:
                PyMem_Free(args.io_counter_per_latency)

            if args.distribution:
                PyMem_Free(args.distribution)

            if args.lba_size_list:
                PyMem_Free(args.lba_size_list)

            if args.lba_size_list_ratio:
                PyMem_Free(args.lba_size_list_ratio)

            if args.lba_size_list_align:
                PyMem_Free(args.lba_size_list_align)

            import gc; gc.collect()


def config(verify, fua_read=False, fua_write=False):
    """config driver global setting

    # Parameters
        verify (bool): enable inline checksum verification of read
        fua_read (bool): enable FUA of read. Default: False
        fua_write (bool): enable FUA of write. Default: False
    """

    return d.driver_config((verify << 0) |
                           (fua_read << 1) |
                           (fua_write << 2))


def srand(seed):
    """setup random seed

    # Parameters
        seed (int): the seed to setup for both python and C library
    """

    global _random_seed
    _random_seed = seed

    logging.info("setup random seed: 0x%x" % seed)
    d.driver_srand(seed)
    random.seed(seed)


# module init, needs root privilege
if os.geteuid() == 0:
    # CTRL-c to exit
    signal.signal(signal.SIGINT, _interrupt_handler)
    # timeout
    signal.signal(signal.SIGALRM, _timeout_signal_handler)

    _reentry_flag_init()

    # config runtime: disable ASLR, 8T drive, S3
    subprocess.call("ulimit -n 10000", shell=True)
    subprocess.call("echo deep > /sys/power/mem_sleep", shell=True)
    subprocess.call("echo 0 > /proc/sys/kernel/randomize_va_space", shell=True)

    # spawn only limited data from parent process
    _mp = multiprocessing.get_context("spawn")

    # init driver
    if d.driver_init() != 0:
        logging.error("driver initialization fail")
        raise SystemExit("driver initialization fail")

    # module fini
    atexit.register(d.driver_fini)
