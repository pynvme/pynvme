#
#  Copyright (C) 2020-2025 GENG YUN Technology Pte. Ltd.
#  All rights reserved.
#
#  NOTICE: All information contained herein is, and remains the
#  property of GENG YUN Technology Pte. Ltd. and its suppliers, if
#  any. The intellectual and technical concepts contained herein are
#  proprietary to GENG YUN Technology Pte. Ltd. and are protected by
#  patent or trade secret or copyright law.
#
#  Dissemination of this information or reproduction of this material
#  is strictly forbidden unless prior written permission is obtained
#  from GENG YUN Technology Pte. Ltd.
#
#  Distribution of source code or binaries derived from this file is
#  not permitted. You should have received a copy of the End User
#  License Agreement along with this program; if not, please contact
#  GENG YUN Technology Pte. Ltd. <sales@pynv.me>

# -*- coding: utf-8 -*-


from __future__ import annotations
_cTIMEOUT = 10

class Buffer:
    def __init__() -> Buffer:
        """ Buffer(length, name='buffer', pvalue=0, ptype=0, offset=0, Controller nvme=None, fake_phys_addr=None, align=4096, prp2=None)

a single chunk of physical-contiguous memory, DMA-safe.

    0              offset                                       length
    |==============|============================================|
                   |<--------------- size --------------->|

    Args:
        length (int): the physical length (in bytes) of the buffer.
        name (str): the name of the buffer. Default: 'buffer'
        pvalue (int): data pattern value. Default: 0
        ptype (int): data pattern type. Default: 0
        offset (int): the starting point presented in PRP/SGL. Default: 0
        nvme (Controller): allocate buffer in the controller's memory buffer (CMB). Default: None
        fake_phys_addr (int): specify the physical address used by PRP/SGL in meta mode. Default: None
        align (int): the alignment address of the physical start of the buffer.
        prp2 (Buffer): when prp2 is given, prp pass-through mode is used in NVMe Admin commands

    # data patterns
```md
        |ptype    | pvalue                                                     |
        |---------|------------------------------------------------------------|
        |0        | 0 for all-zero data, 1 for all-one data                    |
        |32       | 32-bit value of the repeated data pattern                  |
        |0xbeef   | random data compressed rate (0: all 0; 100: fully random)  |
        |0xf17e   | path of the pattern file (type: str)                       |
        |0x1234   | starting number of the increasing pattern, 16-bit. (int)   |
        |0x4321   | starting number of the decreasing pattern, 16-bit. (int)   |
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
        >>> b.data(2, 0) == 0x02015a
        True
        >>> len(b)
        1024
        >>> b
        <buffer name: example>
        >>> b.set_dsm_range(1, 0x1234567887654321, 0xabcdef12)
        >>> b.dump(64)
        buffer
        00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  ................
        00000010  00 00 00 00 12 ef cd ab  21 43 65 87 78 56 34 12  ........!Ce.xV4.
        00000020  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  ................
        00000030  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ................
```
        """
        pass

    def crc8(self):
        """

get crc8 of the buffer 

        """
        pass

    def data(self, byte_end, byte_begin=None, type=int, endian='little') -> int | str:
        """

retrieve the field in the buffer



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. Included. Default: None, means same as byte_end

    type (type): the type of the field to be converted (e.g. int, str). Default: int

    endian (str): the endian. Default: little.



Returns:

    (int or str): the data in the specified field

        """
        pass

    @property
    def data_head(self):
        """  display the first 16-byte of the buffer  """
        pass

    @property
    def data_tail(self):
        """  display the last 16-byte of the buffer  """
        pass

    def diff(self, buf2):
        """

generate diff html output 

        """
        pass

    def distance(self, buf2) -> int:
        """

distance with another buffer 

        """
        pass

    def dump(self, size=None) -> str:
        """

get the buffer data with a human friendly output



Args:

    size (int): the size of the buffer to print. Default: None, to print the whole buffer

        """
        pass

    def fill_pattern(self, pvalue=0, ptype=0):
        """

fill pattern data into the buffer, following ptype/pvalue definition

        

        """
        pass

    def match(self, file_ptn=None) -> Buffer:
        """

find the best match pattern from the pattern file 

        """
        pass

    @property
    def name(self):
        """ Buffer.name: str """
        pass

    @property
    def offset(self):
        """ Buffer.offset: int """
        pass

    @property
    def phys_addr(self):
        """  physical address of the buffer starting from the offset  """
        pass

    def read_16byte(self, offset) -> tuple[int]:
        """

read data from memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

    def set_controller_list(self, *cntlid_list):
        """

set controller id list in buffer



Args:

    cntlid_list (list of int): the list of controller id

        """
        pass

    def set_copy_range(self, index, lba, lba_count, format=0, storage_reference_tag=0, app_tag=0, app_tag_mask=0):
        """

set copy command ranges in the buffer



Args:

    index (int): the index of the copy range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range. 1-based.

    format (int): the format of the copy command range

        """
        pass

    def set_dsm_range(self, index, lba, lba_count, attr=0):
        """

set DSM command ranges in the buffer



Args:

    index (int): the index of the dsm range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range, 1-based.

    attr (int): context attributes of the range. Default: 0

        """
        pass

    @property
    def sgl(self):
        """ Buffer.sgl: bool """
        pass

    @property
    def size(self):
        """ Buffer.size: int """
        pass

    def write_16byte(self, offset, dword0, dword1, dword2, dword3):
        """

write data to memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

class Pcie:
    def __init__() -> Pcie:
        """ Pcie(str addr: str, vf=0, port=0, logdir='results', msi_only=False, core_id=0, slot_id=0)

Pcie class to access PCIe configuration and memory space. Prefer to use fixture "pcie" in test scripts.

Args:
    addr (str): BDF address of PCIe device
    vf (int): virtual function used by sriov. Default: 0
    port (int): TCP/IP port used by NVMe over TCP. Default: 0
    logdir (str): save test logfiles in this directory. Default: 'results'
    msi_only (bool): use MSI instead of MSIx. Default: False.
    core_id (int): the first core allocated for this DUT. Default: 0
    slot_id (int): the DUT slot number in racktester. Default: 0    """
        pass

    @property
    def addr(self):
        """ Pcie.addr: str """
        pass

    @property
    def aspm(self):
        """ Pcie.aspm: int """
        pass

    @property
    def bme(self):
        """ Pcie.bme: bool """
        pass

    def cap_offset(self, cap_id, extend=False) -> int:
        """

find the offset of a capability in configuration space



Args:

    cap_id (int): capability id

    extend (bool): access the extend capabilities



Returns:

    (int): the offset of the register, or None if the capability does not exist

        """
        pass

    def cfg_byte_read(self, addr) -> int:
        """

access byte in pcie config space



Args:

    addr (int): the address (in bytes) of the register in the config space



Returns:

    (int): the value of the register

        """
        pass

    def cfg_byte_write(self, addr, value):
        """

modify byte in pcie config space



Args:

    addr (int): the address (in bytes) of the register in the config space

    value (int): the value of the register

        """
        pass

    def cfg_dword_read(self, addr) -> int:
        """

access dword in pcie config space



Args:

    addr (int): the address (in bytes) of the register in the config space



Returns:

    (int): the value of the register

        """
        pass

    def cfg_dword_write(self, addr, value):
        """

modify dword in pcie config space



Args:

    addr (int): the address (in bytes) of the register in the config space

    value (int): the value of the register

        """
        pass

    def cfg_word_read(self, addr) -> int:
        """

access word in pcie config space



Args:

    addr (int): the address (in bytes) of the register in the config space



Returns:

    (int): the value of the register

        """
        pass

    def cfg_word_write(self, addr, value):
        """

modify word in pcie config space



Args:

    addr (int): the address (in bytes) of the register in the config space

    value (int): the value of the register

        """
        pass

    def close(self):
        """

close pcie object and release resources 

        """
        pass

    def flr(self, c=0):
        """

send function-level reset to the pcie device



Args:

    c (int): vf id, used only when resetting vf on a PF pcie object



Notes:

    call Controller.reset() to re-initialize controller after this reset

        """
        pass

    def link_disable_enable(self):
        """

disable, enable and retrain the PCIe link



Notes:

    call Controller.reset() to re-initialize controller after this reset

        """
        pass

    def mem_byte_read(self, addr) -> int:
        """

access byte in pcie bar0 space



Args:

    addr (int): the address (in bytes) of the register in the bar0 space



Returns:

    (int): the value of the register

        """
        pass

    def mem_byte_write(self, addr, value):
        """

modify byte in pcie bar0 space



Args:

    addr (int): the address (in bytes) of the register in the bar0 space

    value (int): the value of the register

        """
        pass

    def mem_dword_read(self, addr) -> int:
        """

access dword in pcie bar0 space



Args:

    addr (int): the address (in bytes) of the register in the bar0 space



Returns:

    (int): the value of the register

        """
        pass

    def mem_dword_write(self, addr, value):
        """

modify dword in pcie bar0 space



Args:

    addr (int): the address (in bytes) of the register in the bar0 space

    value (int): the value of the register

        """
        pass

    def mem_qword_read(self, addr) -> int:
        """

access qword/8-byte in pcie bar0 space



Args:

    addr (int): the address (in bytes) of the register in the bar0 space



Returns:

    (int): the value of the register

        """
        pass

    def mem_qword_write(self, addr, value):
        """

modify qword/8-byte in pcie bar0 space



Args:

    addr (int): the address (in bytes) of the register in the bar0 space

    value (int): the value of the register

        """
        pass

    def mem_word_read(self, addr) -> int:
        """

access word in pcie bar0 space



Args:

    addr (int): the address (in bytes) of the register in the bar0 space



Returns:

    (int): the value of the register

        """
        pass

    def mem_word_write(self, addr, value):
        """

modify word in pcie bar0 space



Args:

    addr (int): the address (in bytes) of the register in the bar0 space

    value (int): the value of the register

        """
        pass

    @property
    def pcie_rescan_func(self):
        """ Pcie.pcie_rescan_func: callable """
        pass

    @property
    def power_state(self):
        """ Pcie.power_state: int """
        pass

    def register(self, offset, byte_count=4) -> int:
        """

access registers in pcie configuration space



Args:

    offset (int): the offset (in bytes) of the register in the config space

    byte_count (int): the size (in bytes) of the register. Default: 4, dword



Returns:

    (int): the value of the register

        """
        pass

    def rescan(self):
        """        """
        pass

    def reset(self):
        """

reset the pcie device with pcie hot reset



Notes:

    call Controller.reset() to re-initialize controller after this reset

        """
        pass

    @property
    def speed(self):
        """ Pcie.speed: int """
        pass

class Controller:
    def __init__() -> Controller:
        """ Controller(pcie, nvme_init_func=None)

Controller class. Prefer to use fixture "nvme0" in test scripts.

    Args:
        pcie (Pcie): Pcie object for PCIe NVMe SSD device.
        nvme_init_func (callable, bool, None): Default: None.
            True: no nvme init process,
            None: default process,
            callable: user defined process function.

    # Example
```shell
        >>> n = Controller(Pcie('01:00.0'))
        >>> hex(n[0])     # read CAP register
        '0x28030fff'
        >>> hex(n[0x1c])  # read CSTS register
        '0x1'
        >>> n.id_data(23, 4, str)  # get controller identify data
        'TW0546VPLOH007A6003Y'
        >>> n.supports(0x18)
        False
        >>> n.supports(0x80)
        True
        >>> id_buf = Buffer(4096)
        >>> n.identify(id_buf).waitdone()  # send identify command
        >>> id_buf.dump(64)
        buffer
        00000000  a4 14 4b 1b 54 57 30 35  34 36 56 50 4c 4f 48 30  ..K.TW0546VPLOH0
        00000010  30 37 41 36 30 30 33 59  43 41 33 2d 38 44 32 35  07A6003YCA3-8D25
        00000020  36 2d 51 31 31 20 4e 56  4d 65 20 4c 49 54 45 4f  6-Q11 NVMe LITEO
        00000030  4e 20 32 35 36 47 42 20  20 20 20 20 20 20 20 20  N 256GB
```
        """
        pass

    def abort(self, cid, sqid=0, cb=None) -> Controller:
        """

abort command



Args:

    cid (int): command id of the command to be aborted

    sqid (int): sq id of the command to be aborted. Default: 0, to abort the admin command

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def add_monitor(self, name, func, interval=1):
        """

add monitor function to the agent



Args:

    name (str): name of the monitor

    func (callable): function with parameter `nvme0`

    interval (int): interval in seconds between calls to the function

        """
        pass

    @property
    def addr(self):
        """ Controller.addr: str """
        pass

    def aer(self, refill=True, cb=None) -> Controller:
        """

asynchorous event request admin command.



Args:

    refill (bool): control if sending a new AER command after reaping an AER. Default: True

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    @property
    def cap(self):
        """ Controller.cap: int """
        pass

    def cmdlog(self, count=1000, offset=0, sqid=0) -> list[str]:
        """

get the log of recent commands and their completions.



Args:

    count (int): the number of commands in the cmdlog. Default: 1000.

    offset (int): the offset of the command in the cmdlog. Default: 0.

    sqid (int): the qpair of the cmdlog. Default: 0, admin queue

        """
        pass

    def cmdlog_merged(self, count, *qlist) -> list[str]:
        """

get recent commands and their completions from multiple queues



Args:

    count (int): the number of commands in cmdlog.

    qlist (list): the list of the queues (e.g. Controller for admin, Qpair and IOSQ) to get their cmdlog. Default: all exist queues

        """
        pass

    def cmdname(self, opcode) -> str:
        """

get the name of the admin command



Args:

    opcode (int): the opcode of the admin command



Returns:

    (str): the command name

        """
        pass

    def directive_receive(self, buf, doper, dtype, dspec=0, length=None, cdw12=0, cdw13=0, nsid=0, cdw02=0, cdw03=0, cb=None) -> Controller:
        """

admin command: directive receive



Args:

    buf (Buffer): buffer of the data received

    doper (int): directive operation

    dtype (int): directive type

    dspec (int): directive specific

    length (int): bytes of the data to receive, default the same length of the buffer

    cdw12 (int): command dword12

    cdw13 (int): command dword13

    nsid (int): nsid in SQE

    cdw02 (int): command dword02

    cdw03 (int): command dword03

    cb (function): callback function called at cmd completion



Returns:

    self (Controller)

        """
        pass

    def directive_send(self, buf, doper, dtype, dspec=0, length=None, cdw12=0, cdw13=0, nsid=0, cdw02=0, cdw03=0, cb=None) -> Controller:
        """

admin command: directive send



Args:

    buf (Buffer): buffer of the data received

    doper (int): directive operation

    dtype (int): directive type

    dspec (int): directive specific

    length: bytes of the data to receive, default the same length of the buffer

    cdw12 (int): command dword12

    cdw13 (int): command dword13

    nsid (int): nsid in SQE

    cdw02 (int): command dword02

    cdw03 (int): command dword03

    cb (function): callback function called at cmd completion



Returns:

    self (Controller)

        """
        pass

    def downfw(self, filename, slot=0, action=1):
        """

firmware download utility: by 4K, and activate in next reset



Args:

    filename (str): the pathname of the firmware binary file to download

    slot (int): firmware slot field in the command. Default: 0, decided by device

    cb (function): callback function called at completion. Default: None

        """
        pass

    def dst(self, stc=1, nsid=0xffffffff, cb=None) -> Controller:
        """

device self test (DST) admin command



Args:

    stc (int): selftest code (stc) field in the command

    nsid (int): nsid field in the command. Default: 0xffffffff

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def fio(self, nsid, *args):
        """

start fio test with spdk engine in a child process



Args:

    nsid (int): the nsid of the namespace to run fio on.

    args (*tuple): fio parameters.



Notes:

    fio cannot run longer than 12hr.

        """
        pass

    def format(self, lbaf=0, ses=0, nsid=1, pil=0, pi=0, mset=0, cb=None) -> Controller:
        """

format admin command



Notes:

    This Controller.format only send the admin command. Use Namespace.format() to maintain pynvme internal data.



Args:

    lbaf (int): lbaf (lba format) field in the command. Default: 0

    ses (int): ses field in the command. Default: 0, no secure erase

    nsid (int): nsid field in the command. Default: 1

    pil (int): PI location

    pi (int): PI type

    mset (int): mset

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def fw_commit(self, slot, action, bpid=0, cb=None) -> Controller:
        """

firmware commit admin command



Args:

    slot (int): firmware slot field in the command

    action (int): action field in the command

    bpid (int): boot partition id field in the command

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def fw_download(self, buf, offset, size=None, cb=None) -> Controller:
        """

firmware download admin command



Args:

    buf (Buffer): the buffer to hold the firmware data

    offset (int): offset (in bytes) in the firmware image

    size (int): size (in bytes) in the firmware image. Default: None, means the size of the buffer

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def get_adminq_setting(self):
        """

get the admin queue related setttings



Returns:

    (tuple): address of admin SQ, size of admin SQ, address of admin CQ, size of admin CQ

        """
        pass

    def get_cmd(self, cpl):
        """

get the command data struct corresponding to the completion



Args:

    cpl (CQE): the completion data structure as the parameter of the callback function



Returns:

    (SQE): SQE object of the command



Notes:

    This function has to be called in the callback function when the command is available.

        """
        pass

    def get_lba_format(self, data_size=512, meta_size=0, pif=0, sts=0, nsid=0xffffffff) -> int:
        """

find the lba format by its data size and meta data size



Args:

    data_size (int): data size. Default: 512

    meta_size (int): meta data size. Default: 0

    pif (int): protection information format

    sts (int): storage tag size

    nsid (int): nsid of the namespace



Returns:

    (int or None): the lba format has the specified data size and meta data size

        """
        pass

    def get_timeout_ms(self, opcode) -> int:
        """

retrieve timeout of the command



Args:

    opcode (int): operation code

        """
        pass

    def getfeatures(self, fid, sel=0, buf=None, nsid=0, cdw11=0, cdw12=0, cdw13=0, cdw14=0, cdw15=0, cb=None) -> Controller:
        """

getfeatures admin command



Args:

    fid (int): feature id

    sel (int): sel field in the command. Default: 0

    buf (Buffer): the buffer to hold the feature data. Default: None

    nsid (int): nsid field in the command. Default: 0

    cdwxx (int): cdw 11-15 in the command. Default: 0

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def getlogpage(self, lid, buf, size=None, offset=0, nsid=0xffffffff, log_specific_id=0, cb=None) -> Controller:
        """

getlogpage admin command



Args:

    lid (int): Log Page Identifier (16bit including LSP and RAE fields)

    buf (Buffer): buffer to hold the log page

    size (int): size (in byte) of data to get from the log page,. Default: None, means the size is the same of the buffer

    offset (int): the location within a log page

    nsid (int): nsid field in the command. Default: 0xffffffff

    log_specific_id (int): Log Specific Identifier. Default: 0

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def id_data(self, byte_end, byte_begin=None, type=int, nsid=0, cns=1, cntid=0, csi=0, nvmsetid=0) -> int | str:
        """

get field in controller identify data



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end

    type (type): the type of the field. It should be int or str. Default: int, convert to integer python object

    cns (int): cns field in the command. Default: 1

    cntid (int): cntid. Default: 0

    csi (int): csi. Default: 0

    nvmsetid (int): nvmsetid or cns_specific_id for NVMe 2.0. Default: 0



Returns:

    (int or str): the data in the specified field

        """
        pass

    def identify(self, buf, nsid=0, cns=1, cntid=0, csi=0, nvmsetid=0, cns_specific_id=0, cdw14=0, cb=None) -> Controller:
        """

identify admin command



Args:

    buf (Buffer): the buffer to hold the identify data

    nsid (int): nsid field in the command. Default: 0

    cns (int): cns field in the command. Default: 1

    cntid (int): cntid. Default: 0

    csi (int): csi. Default: 0

    nvmsetid (int): obsoleted in NVMe 2.0.

    cns_specific_id (int): CNS Specific Identifier in NVMe 2.0 (aka nvmsetid in NVMe 1.x). Default: 0

    cdw14 (int): command dword14, including UUID Index. Default: 0

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def init_adminq(self, depth=127, skip_register=False, lazy_doorbell=False, reuse_adminq=False) -> int:
        """

used by NVMe init process in scripts to create admin queue and config related registers



Args:

    depth (int): the depth of admin queue, < 4096. Default 127.

    skip_register (bool): not to update admin queue related registers in this function call. Default: False

    lazy_doorbell (bool): trigger doorbell in waitdone. Default: False, trigger doorbell when sending the command

    reuse_adminq (bool): reuse the existed adminq instead of creating another one. Default: False



Returns:

    (int): 0 for SUCCESS



Notes:

    cannot reuse adminq after pcie reset, adminq can only be reused after controller reset

        """
        pass

    def init_ns(self) -> int:
        """

used by NVMe init process in scripts to initialize all namespace 

        """
        pass

    def init_queues(self, cdw0):
        """

used by NVMe init process in scripts to initialize all queues 

        """
        pass

    @property
    def iosq_list(self):
        """ Controller.iosq_list: list[IOSQ] """
        pass

    def iostat(self):
        """

get current performance in list [speed, iops] 

        """
        pass

    @property
    def latest_cid(self):
        """ Controller.latest_cid: int """
        pass

    @property
    def latest_latency(self):
        """ Controller.latest_latency: int """
        pass

    @property
    def latest_status(self):
        """ Controller.latest_status: int """
        pass

    def logdir_filepath(self, filename) -> str:
        """

get the full path name of the file in log directory 

        """
        pass

    def logdir_savefile(self, name, data):
        """

save data to the file in the log directory 

        """
        pass

    @property
    def mdts(self):
        """ Controller.mdts: int """
        pass

    def mi_receive(self, opcode, dword0=0, dword1=0, buf=None, mtype=1, header=0, nsid=0, cb=None) -> Controller:
        """

NVMe MI receive admin command



Args:

    opcode (int): MI opcode

    dword0 (int): MI request dword0

    dword1 (int): MI request dword1

    buf (Buffer): buffer to hold the response data

    mtype (int): MI message type. Default:1, MI command set

    header (int): NVMe-MI message header in cdw10

    nsid (int): nsid, default: 0

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def mi_send(self, opcode, dword0=0, dword1=0, buf=None, mtype=1, header=0, nsid=0, cb=None) -> Controller:
        """

NVMe MI Send admin command



Args:

    opcode (int): MI opcode

    dword0 (int): MI request dword0

    dword1 (int): MI request dword1

    buf (Buffer): buffer to hold the request data

    mtype (int): MI message type. Default:1, MI command set

    header (int): NVMe-MI message header in cdw10

    nsid (int): nsid, default: 0

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def ns_attach(self, nsid, *cntlid_list):
        """

attach namespace to controllers



Args:

    nsid (int): nsid of the ns to be attached

    cntlid_list (list): controller list



Returns:

    None

        """
        pass

    def ns_attachment(self, buf, select, nsid, cb=None) -> Controller:
        """

admin command: namespace attachment



Args:

    buf (Buffer): host buffer of the namespace management

    select (int): the type of attachment operation to perform

    nsid (int): nsid of the ns to be deleted

    cb (function): callback function called at cmd completion



Returns:

    self (Controller)

        """
        pass

    def ns_clear(self, nsid=0xffffffff) -> None:
        """

clear ns crc tables for user's format-like VU commands



Args:

    nsid (int): the nsid of the ns to be cleared. Default: 0xffff_ffff, all namespaces

        """
        pass

    def ns_create(self, buf) -> int:
        """

namespace delete operation



Args:

    buf (Buffer): host buffer of the namespace management



Returns:

    (int) nsid of the namespace created

        """
        pass

    def ns_delete(self, nsid=0xffffffff):
        """

namespace delete operation



Args:

    nsid (int): nsid of the ns to be deleted. Default: 0xffff_ffff, all namespaces



Returns:

    None

        """
        pass

    def ns_detach(self, nsid, *cntlid_list):
        """

detach namespace to controllers



Args:

    nsid (int): nsid of the ns to be detached

    cntlid_list (list): controller list



Returns:

    None

        """
        pass

    def ns_management(self, buf, select, nsid, cb=None) -> Controller:
        """

admin command: namespace management



Args:

    buf (Buffer): host buffer of the namespace management

    select (int): the type of management operation to perform

    nsid (int): nsid of the ns to be deleted

    cb (function): callback function called at cmd completion



Returns:

    self (Controller)

        """
        pass

    @property
    def nvme_init_func(self):
        """ Controller.nvme_init_func: callable """
        pass

    def reset(self, create_qpair=True):
        """

controller reset by cc.en



Args:

    create_qpair (bool): create all qpair existed before reset. Default: True

        """
        pass

    def ring_doorbell(self):
        """

ring doorbell of admin queue manually



Notes:

    The doorbell of admin queue is automatically upadted in waitdone().

        """
        pass

    def sanitize(self, option=2, pattern=0, cb=None) -> Controller:
        """

sanitize admin command



Args:

    option (int): sanitize options in dword10

    pattern (int): pattern field in the command for overwrite method

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def security_receive(self, buf, spsp, secp=1, nssf=0, length=None, nsid=0, cb=None) -> Controller:
        """

admin command: security receive



Args:

    buf (Buffer): buffer of the data received

    spsp: SP specific 0/1, 16bit filed

    secp: security protocal, default 1, TCG

    nssf: NVMe security specific field: default 0, reserved

    length: bytes of the data to receive, default the same length of the buffer

    nsid: The use of the Namespace Identifier is Security Protocol specific, default 0.

    cb (function): callback function called at cmd completion



Returns:

    self (Controller)

        """
        pass

    def security_send(self, buf, spsp, secp=1, nssf=0, length=None, nsid=0, cb=None) -> Controller:
        """

admin command: security send



Args:

    buf (Buffer): buffer of the data sending

    spsp: SP specific 0/1, 16bit filed

    secp: security protocal, default 1, TCG

    nssf: NVMe security specific field: default 0, reserved

    length: bytes of the data to send, default the same length of the buffer

    nsid: The use of the Namespace Identifier is Security Protocol specific, default 0.

    cb (function): callback function called at cmd completion



Returns:

    self (Controller)

        """
        pass

    def send_cmd(self, opcode, buf=None, nsid=0, cdw10=0, cdw11=0, cdw12=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, cb=None) -> Controller:
        """

send generic admin commands. Script can use it to send any kind of admin command, like Vendor Specific command or even not defined command.



Args:

    opcode (int): operate code of the command

    buf (Buffer): buffer of the command. Default: None

    nsid (int): nsid field of the command. Default: 0

    cdwxx (int): cdw10-15, 02-03

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def set_timeout_ms(self, opcode, msec):
        """

set timeout value of the command in primary process



Args:

    opcode (int): operation code

    msec (int): timeout value in milli-second

        """
        pass

    def setfeatures(self, fid, sv=0, buf=None, nsid=0, cdw11=0, cdw12=0, cdw13=0, cdw14=0, cdw15=0, cb=None) -> Controller:
        """

setfeatures admin command



Args:

    fid (int): feature id

    sv (int): sv field in the command. Default: 0

    buf (Buffer): the buffer to hold the feature data. Default: None

    nsid (int): nsid field in the command. Default: 0

    cdwxx (int): cdw 11-15 in the command. Default: 0

    cb (function): callback function called at completion. Default: None



Returns:

    self (Controller)

        """
        pass

    def supports(self, opcode) -> bool:
        """

check if the admin command is supported



Args:

    opcode (int): the opcode of the admin command



Returns:

    (bool): if the command is supported

        """
        pass

    @property
    def tcg_feature_data(self):
        """ Controller.tcg_feature_data: list[int] """
        pass

    @property
    def tcg_feature_list(self):
        """ Controller.tcg_feature_list: list[int] """
        pass

    @property
    def timeout(self):
        """ Controller.timeout: int """
        pass

    @property
    def timeout_pynvme(self):
        """ Controller.timeout_pynvme: int """
        pass

    def timestamp(self) -> str:
        """

get currect date and timestamp 

        """
        pass

    def virt_mgmt(self, vf, action, resource=0, number=0, cb=None) -> Controller:
        """

admin command: virtualization mamangement



Args:

    vf (int): vf

    action (int): action

    resource (int): resource

    number (int): number

    cb (function): callback function called at cmd completion



Returns:

    self (Controller)

        """
        pass

    def wait_csts(self, rdy=None):
        """

wait csts.rdy to be high or low



Args:

    rdy (bool): the expected csts.rdy signal. True is high, False is low.

        """
        pass

    def waitdone(self, expected=1, interrupt_enabled=True) -> int:
        """

sync until expected admin commands completion



Notes:

    Do not call this function in commands callback functions.



Args:

    expected (int): expected commands to complete. Default: 1

    interrupt_enabled (bool): check interrupt table before checking CQ. Default: True for admin queue.



Returns:

    (int): cdw0 of the last command

        """
        pass

class Qpair:
    def __init__() -> Qpair:
        """ Qpair(Controller nvme, unsigned int depth, unsigned int prio=0, bool ien=True, unsigned short iv=0xffff, unsigned int sqid=0, bool lazy_doorbell=False, Buffer sq_buf=None, Buffer cq_buf=None)

Qpair class. IO SQ and CQ are combinded into the qpair. Prefer to use fixture "qpair" in test scripts.

Args:
    nvme (Controller): controller where to create the queue
    depth (int): SQ/CQ queue depth
    prio (int): when Weighted Round Robin is enabled, specify SQ priority here
    ien (bool): interrupt enabled. Default: True
    iv (short): interrupt vector. Default: 0xffff, chosen by driver
    sqid (int): specify a qid. Default: 0, qid is chosen by driver
    lazy_doorbell (bool): trigger doorbell in waitdone. Default: False
    sq_buf (Buffer): the buffer used as SQ. Default: None, created by driver.
    cq_buf (Buffer): the buffer used as CQ. Default: None, created by driver.

Notes:
    If the qpair is created for ioworker, it is good for performance to set ien=False and lazy_doorbell=True. One qpair can only be used in one process at any time.    """
        pass

    def cmdlog(self, count=1000, offset=0) -> list[str]:
        """

print recent IO commands and their completions in this qpair.



Args:

    count (int): the number of commands to print. Default: 1000, to print the latest 1000 cmdlog

    offset (int): the offset of the command in cmdlog. Default: 0, to print the latest cmdlog

        """
        pass

    def delete(self):
        """

delete IOSQ and IOCQ, and release driver resources 

        """
        pass

    @property
    def depth(self):
        """ Qpair.depth: int """
        pass

    def get_cmd(self, cpl):
        """

get the command data struct corresponding to the completion



Args:

    cpl (CQE): the completion data structure as the parameter of the callback function



Returns:

    (SQE): SQE object of the command



Notes:

    This function has to be called in the callback function when the command is available.

        """
        pass

    def int_clear(self):
        """

clear the msi/msix interrupt of the queue 

        """
        pass

    def int_isset(self) -> bool:
        """

check the msi/msix interrupt of the queue 

        """
        pass

    def int_mask(self):
        """

mask the msi/msix interrupt of the queue 

        """
        pass

    def int_unmask(self):
        """

unmask the msi/msix interrupt of the queue 

        """
        pass

    @property
    def latest_cid(self):
        """ Qpair.latest_cid: int """
        pass

    @property
    def latest_latency(self):
        """ Qpair.latest_latency: int """
        pass

    def msix_clear(self):
        """

clear the msix interrupt of the queue 

        """
        pass

    def msix_isset(self) -> bool:
        """

check the msix interrupt of the queue 

        """
        pass

    def msix_mask(self):
        """

mask the msix interrupt of the queue 

        """
        pass

    def msix_unmask(self):
        """

unmask the msix interrupt of the queue 

        """
        pass

    @property
    def prio(self):
        """ Qpair.prio: int """
        pass

    @property
    def sqid(self):
        """ Qpair.sqid: int """
        pass

    def wait_int(self):
        """

wait for the msi/msix interrupt of the queue 

        """
        pass

    def wait_msix(self, timeout=_cTIMEOUT):
        """

wait for the msix interrupt of the queue 

        """
        pass

    def waitdone(self, expected=1) -> int:
        """

sync until expected IO commands completion



Notes:

    Do not call this function in commands callback functions.



Args:

    expected (int): expected commands to complete. Default: 1



Returns:

    (int): cdw0 of the last command

        """
        pass

class Namespace:
    def __init__() -> Namespace:
        """ Namespace(Controller nvme, unsigned int nsid=1, unsigned long nlba_verify=0xffffffffffffffff, crc_snapshot=None)

Namespace class. Prefer to use fixture "nvme0n1" in test scripts.

Args:
    nvme (Controller): controller where to create the queue
    nsid (int): nsid of the namespace. Default 1
    nlba_verify (long): number of LBAs where data verificatoin is enabled. Default 0xffffffff_ffffffff, the whole namespace
    crc_snapshot (str): the path of file to restore crc data. Default: None    """
        pass

    @property
    def capacity(self):
        """ Namespace.capacity: int """
        pass

    def close(self, crc_snapshot=None):
        """

release namespace driver resources.



Args:

    crc_snapshot (str): the path of file to backup crc data. Default: None

        """
        pass

    def cmdname(self, opcode) -> str:
        """

get the name of the IO command



Args:

    opcode (int): the opcode of the IO command



Returns:

    (str): the command name

        """
        pass

    def compare(self, qpair, buf, lba, lba_count=1, io_flags=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, meta=None, cb=None) -> Qpair:
        """

compare IO command



Notes:

    buf cannot be released before the command completes.



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): the data buffer of the command, meta data is not supported.

    lba (int): the starting lba address, 64 bits

    lba_count (int): the lba count of this command, 1-based. Default: 1

    io_flags (short): io flags defined in NVMe specification, 16 bits. Default: 0

    cdw13 (int): command SQE cdw13

    cdw14 (int): command SQE cdw14

    cdw15 (int): command SQE cdw15

    cdw02 (int): command SQE cdw02

    cdw03 (int): command SQE cdw03

    meta (Buffer): the seperated meta data buffer

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def copy(self, qpair, buf, range_count, sdlba, io_flags=0, prinfor=0, format=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, cb=None) -> Qpair:
        """

copy command



Notes:

    buf cannot be released before the command completes.



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): the buffer of the lba ranges. Use buffer.set_dsm_range to prepare the buffer.

    range_count (int): the count of lba ranges in the buffer

    sdlba (int): starting dest LBA

    io_flags (short): io flags defined in NVMe specification, 16 bits. Default: 0

    prinfor (int): protection information for read data (PRACT, PRCHK)

    format (int): format code of the source range entries

    cdw13 (int): command SQE cdw13

    cdw14 (int): command SQE cdw14

    cdw15 (int): command SQE cdw15

    cdw02 (int): command SQE cdw02

    cdw03 (int): command SQE cdw03

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def dsm(self, qpair, buf, range_count, attribute=0x4, cb=None) -> Qpair:
        """

data-set management IO command



Notes:

    buf cannot be released before the command completes.



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): the buffer of the lba ranges. Use buffer.set_dsm_range to prepare the buffer.

    range_count (int): the count of lba ranges in the buffer

    attribute (int): attribute field of the command. Default: 0x4, as deallocation/trim

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def dump_miscompare_lba_disable(self, disable=True) -> bool:
        """

disable the miscompare data dump



Args:

    enable (bool): enable or disable the feature



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def dump_miscompare_lba_enable(self) -> bool:
        """

enable the miscompare data dump



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def flush(self, qpair, cb=None) -> Qpair:
        """

flush IO command



Args:

    qpair (Qpair): use the qpair to send this command

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def format(self, data_size=None, meta_size=0, ses=0, pil=0, pi=0, mset=0, pif=0, sts=0) -> int:
        """

change the format of this namespace



Notes:

    Namespace.format() not only sends the admin command, but also wait the command completed and update crc table. Recommend to use this API to do format. Close and re-create namespace when lba format is changed.



Args:

    data_size (int): data size. Default: None, use the current LBA format

    meta_size (int): meta data size. Default: 0

    ses (int): ses field in the command. Default: 0, no secure erase

    pil (int): PI location

    pi (int): PI type

    mset (int): Metadata setting

    pif (int): Protection Information Format

    sts (int): Storage Tag Size



Returns:

    (int): cdw0 of the format admin command

        """
        pass

    def get_lba_format(self, data_size=512, meta_size=0, pif=0, sts=0) -> int:
        """

find the lba format by its data size and meta data size



Args:

    data_size (int): data size. Default: 512

    meta_size (int): meta data size. Default: 0



Returns:

    (int or None): the lba format has the specified data size and meta data size

        """
        pass

    def get_sector_size(self, extended=False, io_flags=0) -> int:
        """

current sector size of the namespace



Args:

    extended (bool): get the extended sector size. Default: False



Returns:

    (int): the sector size

        """
        pass

    def get_timeout_ms(self, opcode) -> int:
        """

retrieve timeout in milli-second of the IO command



Args:

    opcode (int): operation code



Returns:

    (int): the timeout of the IO command

        """
        pass

    def id_data(self, byte_end, byte_begin=None, type=int, cns=0, cntid=0, csi=0) -> int | str:
        """

get field in namespace identify data



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end

    type (type): the type of the field. It should be int or str. Default: int, convert to integer python object

    cns (int): cns field in the command. Default: 1

    cntid (int): cntid. Default: 0

    csi (int): csi. Default: 0



Returns:

    (int or str): the data in the specified field

        """
        pass

    def inject_write_buffer_disable(self, disable=True) -> bool:
        """

disable the injection write buffer with LBA and token, which is enabled by default.



Args:

    enable (bool): enable or disable the feature



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def inject_write_buffer_enable(self) -> bool:
        """

enable the injection write buffer with LBA and token, which is enabled by default.



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def inject_write_token_disable(self, disable=True) -> bool:
        """

disable the injection write token, which is enabled by default.



Args:

    enable (bool): enable or disable the feature



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def inject_write_token_enable(self) -> bool:
        """

enable the injection write token, which is enabled by default.



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def ioworker(self, qpair=None, io_size=8, lba_step=None, lba_align=None, lba_random=True, read_percentage=100, op_percentage=None, sgl_percentage=0, time=0, qdepth=63, region_start=0, region_end=0xffffffffffffffff, region_end_truncate=True, iops=0, io_count=0, lba_count=0, io_flags=0, lba_start=0, qprio=0, distribution=None, ptype=0xbeef, pvalue=100, cdw13=0, io_sequence=None, slow_latency=1000000, fw_debug=False, exit_on_error=True, retry_max=0, verify_disable=False, zns=False, zns_zigzag=False, zns_syncwrite=False, cpu_id=1, cmdlog_error_only=False, output_io_per_second=None, output_percentile_latency=None, output_percentile_latency_opcode=None, output_cmdlog_list=None):
        """

workers sending different read/write IO on different CPU cores.



User defines IO characteristics in parameters, and then the ioworker

executes without user intervesion, until the test is completed. IOWorker

returns some statistic data at last.



User can start multiple IOWorkers, and they will be binded to different

CPU cores. Each IOWorker creates its own Qpair, so active IOWorker counts

is limited by maximum IO queues that DUT can provide.



Each ioworker can run upto 24 hours.



It is recommended to create qpair explicitly outside of ioworker.



Args:

    qpair (Qpair): reuse the existed qpair. Default: None, ioworker creates the qpair

    io_size (short, range, list, dict): IO size, unit is LBA. It can be a fixed size, or a range or list of size, or specify ratio in the dict if they are not evenly distributed. 1base. Default: 8, 4K

    lba_step (signed int): valid only for sequential read/write, jump to next LBA by the step. Default: None, same as io_size, continous IO.

    lba_align (short, list): IO alignment, unit is LBA. Default: None: means 1 lba.

    lba_random (int, bool): percentage of radom io, or True if sending IO with all random starting LBA. Default: True

    read_percentage (int): sending read/write mixed IO, 0 means write only, 100 means read only. Default: 100. Obsoloted by op_percentage

    op_percentage (dict): opcode of commands sent in ioworker, and their percentage. Output: real io counts sent in ioworker. Default: None, fall back to read_percentage

    sgl_percentage (int): use sgl for data buffer. 0 means only PRP, 100 means only SGL. Default: 0.

    time (int): specified maximum time of the IOWorker in seconds, up to 1000*3600. Default:0, means no limit

    qdepth (int): queue depth of the Qpair created by the IOWorker. 1base value. Default: 63

    region_start (long, list): sending IO in the specified LBA region, start. Default: 0

    region_end (long, list): sending IO in the specified LBA region, end but not include. Default: 0xffff_ffff_ffff_ffff

    region_end_truncate (bool): truncate LBA exceeding the region end. Default: True

    iops (int): specified maximum IOPS. IOWorker throttles the sending IO speed. Default: 0, means no limit

    io_count (long): specified maximum IO counts to send. Default: 0, means no limit

    lba_count (long): specified maximum LBA counts to send. Default: 0, means no limit

    io_flags (short): upper 16-bit in dword12. Default: 0.

    lba_start (long): the LBA address of the first command. Default: 0, means start from region_start

    qprio (int): SQ priority. Default: 0, as Round Robin arbitration

    distribution (list(int)): distribute 10,000 IO to 100 sections. Default: None

    ptype (int): data pattern type. Refer to data pattern in class `Buffer`. Default: 0xbeef (random data)

    pvalue (int): data pattern value. Refer to data pattern in class `Buffer`. Default: 100 (100%)

    cdw13 (int): command dword 13 for directive and DSM. Default: 0.

    io_sequence (list): io sequence of captured trace from real workload. Ignore other input parameters when io_sequence is given. (slba, nlb, opcode, time_sent_us) Default: None

    slow_latency (int): show warning message when the io latency is larger than the criteria in micro-second. Default: 1000_000us (1s)

    fw_debug (bool): skip QPair deletion in exiting failed IOWorker instance. Default: False

    exit_on_error (bool): exit ioworker immediately when any IO command fails. Default: True

    retry_max (int): max times of read retry when data mismatch found. Default: 0, no retry.

    verify_disable (bool): disable the crc verification function. Default: False

    zns (bool): run ioworker on ZNS devices. Default: False

    zns_zigzag (bool): send IO across all zones in the zone list. Default: False

    zns_syncwrite (bool): limit single IO in one zone. Default: False

    cpu_id (int): run ioworker on this cpu core. Default: 1, specify the cpu core allocted to the slot

    cmdlog_error_only (bool): only keep error commands in cmdlog. Default: False

    output_io_per_second (list): list to hold the output data of io_per_second. Default: None, not to collect the data

    output_percentile_latency (dict): dict of io counter on different percentile latency. Dict key is the percentage, and the value is the latency in micro-second. Default: None, not to collect the data

    output_percentile_latency_opcode (int): only trace the latency of opcode. Defalut: None, all opcodes

    output_cmdlog_list (list): lastest commands sent in the ioworker: (slba, nlb, opcode, time_sent_us, time_cplt_us, status) Default: None, not to collect the data



Returns:

    ioworker instance

        """
        pass

    def load_crc(self, crc_snapshot) -> bool:
        """

restore crc image by loading snapshot file



Args:

    crc_snapshot (str): the path of file to backup crc data. Default: None



Returns:

    (bool): load crc successfully or not

        """
        pass

    def mark_nomapping(self, lba, lba_count, uncorr=False):
        """

mark a LBA range nomapping in driver 

        """
        pass

    @property
    def meta_size(self):
        """ Namespace.meta_size: int """
        pass

    @property
    def nsid(self):
        """ Namespace.nsid: int """
        pass

    def pi_engine_disable(self) -> bool:
        """

Disable the PI (Protection Information) engine.



Returns:

   (bool): True if the operation was successful, False otherwise.

        """
        pass

    def pi_engine_enable(self, enable=True) -> bool:
        """

Enable or disable the PI (Protection Information) engine.



Args:

   enable (bool): True to enable PI engine, False to disable it.



Returns:

   (bool): True if the operation was successful, False otherwise.

        """
        pass

    def print_miscompare_log_disable(self, disable=True) -> bool:
        """

disable printing miscompare log



Args:

    enable (bool): enable or disable the feature



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def print_miscompare_log_enable(self) -> bool:
        """

enable printing miscompare log



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def read(self, qpair, buf, lba, lba_count=1, io_flags=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, meta=None, verify_disable=False, cb=None) -> Qpair:
        """

read IO command



Notes:

    buf cannot be released before the command completes.



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): the data buffer of the command

    lba (int): the starting lba address, 64 bits

    lba_count (int): the lba count of this command, 1-based. Default: 1

    io_flags (short): io flags defined in NVMe specification, 16 bits. Default: 0

    cdw13 (int): command SQE cdw13

    cdw14 (int): command SQE cdw14

    cdw15 (int): command SQE cdw15

    cdw02 (int): command SQE cdw02

    cdw03 (int): command SQE cdw03

    meta (Buffer): the seperated meta data buffer

    verify_disable (bool): disable the crc verification on this read command

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def reservation_acquire(self, qpair, buf, rtype=0, iekey=0, racqa=0, crkey=0, prkey=0, cb=None) -> Qpair:
        """

Reservation Acquire command



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): Buffer to store reservation keys, minimum 16 bytes.

    rtype (int): Reservation Type, 8 bits

    iekey (int): Ignore Existing Key, 1 bit.

    racqa (int): Reservation Acquire Action, 3 bits.

    crkey (int): Current Reservation Key, 8 Bytes.

    prkey (int): Preempt Reservation Key, 8 Bytes.

    cb (function): callback function called at completion. Default: None



Notes:

    buf cannot be released before the command completes.



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def reservation_register(self, qpair, buf, cptpl=0, iekey=0, rrega=0, crkey=0, nrkey=0, cb=None) -> Qpair:
        """

Reservation Register command



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): Buffer to store reservation keys, minimum 16 bytes.

    cptpl (int): Change Persist Through Power Loss State, 2 bits

    iekey (int): Ignore Existing Key, 1 bit.

    rrega (int): Reservation Register Action, 3 bits.

    crkey (int): Current Reservation Key, 8 Bytes.

    nrkey (int): Preempt Reservation Key, 8 Bytes.

    cb (function): callback function called at completion. Default: None



Notes:

    buf cannot be released before the command completes.



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def reservation_release(self, qpair, buf, rtype=0, iekey=0, rrela=0, crkey=0, cb=None) -> Qpair:
        """

Reservation Release command



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): Buffer to store reservation key, minimum 8 bytes.

    rtype (int): Reservation Type, 8 bits.

    iekey (int): Ignore Existing Key, 1 bit.

    rrela (int): Reservation Release Action, 3 bits.

    crkey (int): Current Reservation Key, 8 Bytes.

    cb (function): callback function called at completion. Default: None



Notes:

    buf cannot be released before the command completes.



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def reservation_report(self, qpair, buf, numd=None, eds=0, cb=None) -> Qpair:
        """

Reservation Report command



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): Buffer to store the reservation status data, size should be at least (numd * 4) bytes.

    numd (int): Number of Dwords, 32 bits

    eds (int): Extended Data Structure, 1 bit.

    cb (function): callback function called at completion. Default: None



Notes:

    buf cannot be released before the command completes.



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def save_crc(self, crc_snapshot) -> bool:
        """

dump crc image to snapshot file



Args:

    crc_snapshot (str): the path of file to backup crc data. Default: None



Returns:

    (bool): load crc successfully or not

        """
        pass

    @property
    def sector_size(self):
        """ Namespace.sector_size: int """
        pass

    def send_cmd(self, opcode, qpair, buf=None, nsid=None, cdw10=0, cdw11=0, cdw12=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, meta=None, cb=None) -> Qpair:
        """

send generic IO commands. Script can use it to send any kinds of IO command, like Vendor Specific commands or even not defined command.



Args:

    opcode (int): operate code of the command

    qpair (Qpair): qpair used to send this command

    buf (Buffer): buffer of the command. Default: None

    nsid (int): nsid field of the command. Default: 0

    cdwxx (int): cdw10-15, 02-03

    meta (Buffer): buffer of metadata. Default: None

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call

        """
        pass

    def set_timeout_ms(self, opcode, msec):
        """

set timeout value of the IO command



Args:

    opcode (int): operation code

    msec (int): timeout in msec

        """
        pass

    def supports(self, opcode) -> bool:
        """

check if the IO command is supported



Args:

    opcode (int): the opcode of the IO command



Returns:

    (bool): if the command is supported

        """
        pass

    def verify(self, qpair, lba, lba_count=1, io_flags=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, cb=None) -> Qpair:
        """

verify IO command



Args:

    qpair (Qpair): use the qpair to send this command

    lba (int): the starting lba address, 64 bits

    lba_count (int): the lba count of this command, 1-based. Default: 1

    io_flags (short): io flags defined in NVMe specification, 16 bits. Default: 0

    cdw13 (int): command SQE cdw13

    cdw14 (int): command SQE cdw14

    cdw15 (int): command SQE cdw15

    cdw02 (int): command SQE cdw02

    cdw03 (int): command SQE cdw03

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def verify_enable(self, enable=True) -> bool:
        """

enable or disable the data verification function of the namespace



Args:

    enable (bool): enable or disable the verify function



Returns:

    (bool): if it is enabled successfully

        """
        pass

    def write(self, qpair, buf, lba, lba_count=1, io_flags=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, meta=None, cb=None) -> Qpair:
        """

write IO command



Notes:

    buf cannot be released before the command completes.



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): the data buffer of the write command

    lba (int): the starting lba address, 64 bits

    lba_count (int): the lba count of this command, 1-based. Default: 1

    io_flags (short): io flags defined in NVMe specification, 16 bits. Default: 0

    cdw13 (int): command SQE cdw13

    cdw14 (int): command SQE cdw14

    cdw15 (int): command SQE cdw15

    cdw02 (int): command SQE cdw02

    cdw03 (int): command SQE cdw03

    meta (Buffer): the seperated meta data buffer

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def write_uncorrectable(self, qpair, lba, lba_count=1, cb=None) -> Qpair:
        """

write uncorrectable IO command



Args:

    qpair (Qpair): use the qpair to send this command

    lba (int): the starting lba address, 64 bits

    lba_count (int): the lba count of this command, 1-based. Default: 1

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def write_zeroes(self, qpair, lba, lba_count=1, io_flags=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, cb=None) -> Qpair:
        """

write zeroes IO command



Args:

    qpair (Qpair): use the qpair to send this command

    lba (int): the starting lba address, 64 bits

    lba_count (int): the lba count of this command, 1-based. Default: 1

    io_flags (short): io flags defined in NVMe specification, 16 bits. Default: 0

    cdw13 (int): command SQE cdw13

    cdw14 (int): command SQE cdw14

    cdw15 (int): command SQE cdw15

    cdw02 (int): command SQE cdw02

    cdw03 (int): command SQE cdw03

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def zns_mgmt_receive(self, qpair, buf, slba, dwords=None, extended=False, state=0, partial=False, cb=None) -> Qpair:
        """

zns management receive command



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): the buffer

    slba (int): the starting LBA of the zone, 64 bits

    dwords (int): Default: None, decided by the buffer size

    extended (bool): Default: False.

    state (int): state. Default: 0

    partial (bool): Default: False

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

    def zns_mgmt_send(self, qpair, buf, slba, action, select_all=False, cb=None) -> Qpair:
        """

zns management send command



Args:

    qpair (Qpair): use the qpair to send this command

    buf (Buffer): the buffer

    slba (int): the starting LBA of the zone, 64 bits

    action (int): action

    select_all (bool): Default: False

    cb (function): callback function called at completion. Default: None



Returns:

    qpair (Qpair): the qpair used to send this command, for ease of chained call



Raises:

    SystemError: the command fails to send

        """
        pass

class Subsystem:
    def __init__() -> Subsystem:
        """ Subsystem(Controller nvme, poweron_cb=None, poweroff_cb=None)

Subsystem class. Prefer to use fixture "subsystem" in test scripts.

Args:
    nvme (Controller): the nvme controller object of that subsystem
    poweron_cb (func): callback of poweron function
    poweroff_cb (func): callback of poweroff function    """
        pass

    def power_cycle(self, sec=15):
        """

power off and on in seconds with S3/RTC



Notes:

    call Controller.reset() to re-initialize controller after this power cycle



Args:

    sec (int): the seconds between power off and power on. Default: 15.

        """
        pass

    def poweroff(self):
        """

power off the device with poweroff callback 

        """
        pass

    def poweron(self, quick=True):
        """

power on the device with poweron callback



Notes:

    call Controller.reset() to re-initialize controller after this power on



Args:

    quick (bool): obsoloted

        """
        pass

    def reset(self):
        """

reset the nvme subsystem through register nssr.nssrc



Notes:

    call Controller.reset() to re-initialize controller after this reset

        """
        pass

    def shutdown_notify(self, abrupt=False, timeout=_cTIMEOUT):
        """

shutdown notify through register cc.shn



Notes:

    RTD3 entry latency waited in normal shutdown notification



Args:

    abrupt (bool): it will be an abrupt shutdown (return immediately) or clean shutdown (wait shutdown completed). Default: False

    timeout (int): timeout to wait csts.shst. Default: 10s

        """
        pass

class CQE:
    def __init__() -> CQE:
        """  CQE data structure     """
        pass

    @property
    def append(self):
        """ Append object to the end of the list. """
        pass

    def cdw0(self):
        """        """
        pass

    def cid(self):
        """        """
        pass

    @property
    def clear(self):
        """ Remove all items from list. """
        pass

    @property
    def copy(self):
        """ Return a shallow copy of the list. """
        pass

    @property
    def count(self):
        """ Return number of occurrences of value. """
        pass

    def crd(self):
        """        """
        pass

    def dnr(self):
        """        """
        pass

    @property
    def extend(self):
        """ Extend list by appending elements from the iterable. """
        pass

    @property
    def index(self):
        """ Return first index of value. """
        pass

    @property
    def insert(self):
        """ Insert object before index. """
        pass

    def m(self):
        """        """
        pass

    def p(self):
        """        """
        pass

    @property
    def remove(self):
        """ Remove first occurrence of value. """
        pass

    @property
    def reverse(self):
        """ Reverse *IN PLACE*. """
        pass

    def sc(self):
        """        """
        pass

    def sct(self):
        """        """
        pass

    @property
    def sort(self):
        """ Sort the list in ascending order and return None. """
        pass

    def sqhd(self):
        """        """
        pass

    def sqid(self):
        """        """
        pass

    def status(self):
        """        """
        pass

class SQE:
    def __init__() -> SQE:
        """  SQE data structure     """
        pass

    @property
    def append(self):
        """ Append object to the end of the list. """
        pass

    def cid(self):
        """        """
        pass

    @property
    def clear(self):
        """ Remove all items from list. """
        pass

    @property
    def copy(self):
        """ Return a shallow copy of the list. """
        pass

    @property
    def count(self):
        """ Return number of occurrences of value. """
        pass

    @property
    def extend(self):
        """ Extend list by appending elements from the iterable. """
        pass

    @property
    def index(self):
        """ Return first index of value. """
        pass

    @property
    def insert(self):
        """ Insert object before index. """
        pass

    def mptr(self):
        """        """
        pass

    def nlb(self):
        """

1-based 

        """
        pass

    def nsid(self):
        """        """
        pass

    def opc(self):
        """        """
        pass

    def opcode(self):
        """        """
        pass

    def prp1(self):
        """        """
        pass

    def prp2(self):
        """        """
        pass

    @property
    def remove(self):
        """ Remove first occurrence of value. """
        pass

    @property
    def reverse(self):
        """ Reverse *IN PLACE*. """
        pass

    def sgl(self):
        """        """
        pass

    def slba(self):
        """        """
        pass

    @property
    def sort(self):
        """ Sort the list in ascending order and return None. """
        pass

class IOCQ:
    def __init__() -> IOCQ:
        """  IO completion queue

    Args:
        ctrlr (Controller):
        qid (int):
        qsize (int): 1based value
        prp1 (Buffer, PRPList):
        iv (int, None): interrupt vector
        ien (bool): interrupt enabled
        """
        pass

    def delete(self, qid=None):
        """

delete this IOCQ 

        """
        pass

    def head(self):
        """

get the current head doorbell of IOCQ 

        """
        pass

    def wait_pbit(self, index, expected, timeout=_cTIMEOUT):
        """

wait the p-bit of a CQE slot changed as expected



Args:

    expected (int): expected p-bit value.

    timeout (int): timeout in seconds. Default: 10s

        """
        pass

    def waitdone(self, expected=1, timeout=_cTIMEOUT):
        """

sync until expected IO commands completion in meta mode



Args:

    expected (int): expected commands to complete. Default: 1

    timeout (int): timeout in seconds. Default: 10s

        """
        pass

class IOSQ:
    def __init__() -> IOSQ:
        """ create IO submission queue

    Args:
        ctrlr (Controller):
        qid (int):
        qsize (int): 1based value
        prp1 (PRP, PRPList): the location of the queue
        cqid (int): obsoleted. Use cq please.
        pc (bool): physical contiguous
        qprio (int):
        nvmsetid (int):
        cq (IOCQ): CQ binded to this SQ
        """
        pass

    def cmdlog(self, count=1000, offset=0):
        """

get recent commands and their completions.



Args:

    count (int): the number of commands to print. Default: 1000, to print the latest 1000 cmdlog

    offset (int): the offset of the command in cmdlog. Default: 0, to print the latest cmdlog

        """
        pass

    def delete(self, qid=None):
        """

delete the IOSQ 

        """
        pass

    def flush(self, cid, nsid, cb=None):
        """

meta mode IO command: flush 

        """
        pass

    def read(self, cid, nsid, lba, lba_count=1, mptr=None, prp1=None, prp2=None, sgl=None, cb=None):
        """

meta mode IO command: read 

        """
        pass

    def send_cmd(self, opcode, cid, nsid, mptr=None, prp1=None, prp2=None, sgl=None, psdt=0, cdw10=0, cdw11=0, cdw12=0, cdw13=0, cdw14=0, cdw15=0, cdw02=0, cdw03=0, cb=None):
        """

meta mode IO command: generic 

        """
        pass

    def tail(self):
        """

get the current tail doorbell 

        """
        pass

    def write(self, cid, nsid, lba, lba_count=1, mptr=None, prp1=None, prp2=None, sgl=None, cb=None):
        """

meta mode IO command: write 

        """
        pass

    def zns_mgmt_receive(self, cid, nsid, slba, prp1=None, prp2=None, sgl=None, dwords=None, extended=False, state=0, partial=False, cb=None):
        """

meta mode IO command: zns mgmt receive 

        """
        pass

    def zns_mgmt_send(self, cid, nsid, slba, action, prp1=None, prp2=None, sgl=None, select_all=False, cb=None):
        """

meta mode IO command: zns mgmt send 

        """
        pass

class SGL:
    def __init__() -> SGL:
        """  SGL data structure     """
        pass

    def crc8(self):
        """

get crc8 of the buffer 

        """
        pass

    def data(self, byte_end, byte_begin=None, type=int, endian='little') -> int | str:
        """

retrieve the field in the buffer



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. Included. Default: None, means same as byte_end

    type (type): the type of the field to be converted (e.g. int, str). Default: int

    endian (str): the endian. Default: little.



Returns:

    (int or str): the data in the specified field

        """
        pass

    @property
    def data_head(self):
        """  display the first 16-byte of the buffer  """
        pass

    @property
    def data_tail(self):
        """  display the last 16-byte of the buffer  """
        pass

    def diff(self, buf2):
        """

generate diff html output 

        """
        pass

    def distance(self, buf2) -> int:
        """

distance with another buffer 

        """
        pass

    def dump(self, size=None) -> str:
        """

get the buffer data with a human friendly output



Args:

    size (int): the size of the buffer to print. Default: None, to print the whole buffer

        """
        pass

    def fill_pattern(self, pvalue=0, ptype=0):
        """

fill pattern data into the buffer, following ptype/pvalue definition

        

        """
        pass

    def match(self, file_ptn=None) -> Buffer:
        """

find the best match pattern from the pattern file 

        """
        pass

    @property
    def name(self):
        """ Buffer.name: str """
        pass

    @property
    def offset(self):
        """ Buffer.offset: int """
        pass

    @property
    def phys_addr(self):
        """  physical address of the buffer starting from the offset  """
        pass

    def read_16byte(self, offset) -> tuple[int]:
        """

read data from memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

    def set_controller_list(self, *cntlid_list):
        """

set controller id list in buffer



Args:

    cntlid_list (list of int): the list of controller id

        """
        pass

    def set_copy_range(self, index, lba, lba_count, format=0, storage_reference_tag=0, app_tag=0, app_tag_mask=0):
        """

set copy command ranges in the buffer



Args:

    index (int): the index of the copy range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range. 1-based.

    format (int): the format of the copy command range

        """
        pass

    def set_dsm_range(self, index, lba, lba_count, attr=0):
        """

set DSM command ranges in the buffer



Args:

    index (int): the index of the dsm range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range, 1-based.

    attr (int): context attributes of the range. Default: 0

        """
        pass

    @property
    def sgl(self):
        """ Buffer.sgl: bool """
        pass

    @property
    def size(self):
        """ Buffer.size: int """
        pass

    def write_16byte(self, offset, dword0, dword1, dword2, dword3):
        """

write data to memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

class SegmentSGL:
    def __init__() -> SegmentSGL:
        """ None    """
        pass

    def crc8(self):
        """

get crc8 of the buffer 

        """
        pass

    def data(self, byte_end, byte_begin=None, type=int, endian='little') -> int | str:
        """

retrieve the field in the buffer



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. Included. Default: None, means same as byte_end

    type (type): the type of the field to be converted (e.g. int, str). Default: int

    endian (str): the endian. Default: little.



Returns:

    (int or str): the data in the specified field

        """
        pass

    @property
    def data_head(self):
        """  display the first 16-byte of the buffer  """
        pass

    @property
    def data_tail(self):
        """  display the last 16-byte of the buffer  """
        pass

    def diff(self, buf2):
        """

generate diff html output 

        """
        pass

    def distance(self, buf2) -> int:
        """

distance with another buffer 

        """
        pass

    def dump(self, size=None) -> str:
        """

get the buffer data with a human friendly output



Args:

    size (int): the size of the buffer to print. Default: None, to print the whole buffer

        """
        pass

    def fill_pattern(self, pvalue=0, ptype=0):
        """

fill pattern data into the buffer, following ptype/pvalue definition

        

        """
        pass

    def match(self, file_ptn=None) -> Buffer:
        """

find the best match pattern from the pattern file 

        """
        pass

    @property
    def name(self):
        """ Buffer.name: str """
        pass

    @property
    def offset(self):
        """ Buffer.offset: int """
        pass

    @property
    def phys_addr(self):
        """  physical address of the buffer starting from the offset  """
        pass

    def read_16byte(self, offset) -> tuple[int]:
        """

read data from memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

    def set_controller_list(self, *cntlid_list):
        """

set controller id list in buffer



Args:

    cntlid_list (list of int): the list of controller id

        """
        pass

    def set_copy_range(self, index, lba, lba_count, format=0, storage_reference_tag=0, app_tag=0, app_tag_mask=0):
        """

set copy command ranges in the buffer



Args:

    index (int): the index of the copy range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range. 1-based.

    format (int): the format of the copy command range

        """
        pass

    def set_dsm_range(self, index, lba, lba_count, attr=0):
        """

set DSM command ranges in the buffer



Args:

    index (int): the index of the dsm range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range, 1-based.

    attr (int): context attributes of the range. Default: 0

        """
        pass

    @property
    def sgl(self):
        """ Buffer.sgl: bool """
        pass

    @property
    def size(self):
        """ Buffer.size: int """
        pass

    def write_16byte(self, offset, dword0, dword1, dword2, dword3):
        """

write data to memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

class LastSegmentSGL:
    def __init__() -> LastSegmentSGL:
        """ None    """
        pass

    def crc8(self):
        """

get crc8 of the buffer 

        """
        pass

    def data(self, byte_end, byte_begin=None, type=int, endian='little') -> int | str:
        """

retrieve the field in the buffer



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. Included. Default: None, means same as byte_end

    type (type): the type of the field to be converted (e.g. int, str). Default: int

    endian (str): the endian. Default: little.



Returns:

    (int or str): the data in the specified field

        """
        pass

    @property
    def data_head(self):
        """  display the first 16-byte of the buffer  """
        pass

    @property
    def data_tail(self):
        """  display the last 16-byte of the buffer  """
        pass

    def diff(self, buf2):
        """

generate diff html output 

        """
        pass

    def distance(self, buf2) -> int:
        """

distance with another buffer 

        """
        pass

    def dump(self, size=None) -> str:
        """

get the buffer data with a human friendly output



Args:

    size (int): the size of the buffer to print. Default: None, to print the whole buffer

        """
        pass

    def fill_pattern(self, pvalue=0, ptype=0):
        """

fill pattern data into the buffer, following ptype/pvalue definition

        

        """
        pass

    def match(self, file_ptn=None) -> Buffer:
        """

find the best match pattern from the pattern file 

        """
        pass

    @property
    def name(self):
        """ Buffer.name: str """
        pass

    @property
    def offset(self):
        """ Buffer.offset: int """
        pass

    @property
    def phys_addr(self):
        """  physical address of the buffer starting from the offset  """
        pass

    def read_16byte(self, offset) -> tuple[int]:
        """

read data from memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

    def set_controller_list(self, *cntlid_list):
        """

set controller id list in buffer



Args:

    cntlid_list (list of int): the list of controller id

        """
        pass

    def set_copy_range(self, index, lba, lba_count, format=0, storage_reference_tag=0, app_tag=0, app_tag_mask=0):
        """

set copy command ranges in the buffer



Args:

    index (int): the index of the copy range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range. 1-based.

    format (int): the format of the copy command range

        """
        pass

    def set_dsm_range(self, index, lba, lba_count, attr=0):
        """

set DSM command ranges in the buffer



Args:

    index (int): the index of the dsm range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range, 1-based.

    attr (int): context attributes of the range. Default: 0

        """
        pass

    @property
    def sgl(self):
        """ Buffer.sgl: bool """
        pass

    @property
    def size(self):
        """ Buffer.size: int """
        pass

    def write_16byte(self, offset, dword0, dword1, dword2, dword3):
        """

write data to memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

class DataBlockSGL:
    def __init__() -> DataBlockSGL:
        """ None    """
        pass

    def crc8(self):
        """

get crc8 of the buffer 

        """
        pass

    def data(self, byte_end, byte_begin=None, type=int, endian='little') -> int | str:
        """

retrieve the field in the buffer



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. Included. Default: None, means same as byte_end

    type (type): the type of the field to be converted (e.g. int, str). Default: int

    endian (str): the endian. Default: little.



Returns:

    (int or str): the data in the specified field

        """
        pass

    @property
    def data_head(self):
        """  display the first 16-byte of the buffer  """
        pass

    @property
    def data_tail(self):
        """  display the last 16-byte of the buffer  """
        pass

    def diff(self, buf2):
        """

generate diff html output 

        """
        pass

    def distance(self, buf2) -> int:
        """

distance with another buffer 

        """
        pass

    def dump(self, size=None) -> str:
        """

get the buffer data with a human friendly output



Args:

    size (int): the size of the buffer to print. Default: None, to print the whole buffer

        """
        pass

    def fill_pattern(self, pvalue=0, ptype=0):
        """

fill pattern data into the buffer, following ptype/pvalue definition

        

        """
        pass

    def match(self, file_ptn=None) -> Buffer:
        """

find the best match pattern from the pattern file 

        """
        pass

    @property
    def name(self):
        """ Buffer.name: str """
        pass

    @property
    def offset(self):
        """ Buffer.offset: int """
        pass

    @property
    def phys_addr(self):
        """  physical address of the buffer starting from the offset  """
        pass

    def read_16byte(self, offset) -> tuple[int]:
        """

read data from memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

    def set_controller_list(self, *cntlid_list):
        """

set controller id list in buffer



Args:

    cntlid_list (list of int): the list of controller id

        """
        pass

    def set_copy_range(self, index, lba, lba_count, format=0, storage_reference_tag=0, app_tag=0, app_tag_mask=0):
        """

set copy command ranges in the buffer



Args:

    index (int): the index of the copy range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range. 1-based.

    format (int): the format of the copy command range

        """
        pass

    def set_dsm_range(self, index, lba, lba_count, attr=0):
        """

set DSM command ranges in the buffer



Args:

    index (int): the index of the dsm range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range, 1-based.

    attr (int): context attributes of the range. Default: 0

        """
        pass

    @property
    def sgl(self):
        """ Buffer.sgl: bool """
        pass

    @property
    def size(self):
        """ Buffer.size: int """
        pass

    def write_16byte(self, offset, dword0, dword1, dword2, dword3):
        """

write data to memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

class BitBucketSGL:
    def __init__() -> BitBucketSGL:
        """ None    """
        pass

    def crc8(self):
        """

get crc8 of the buffer 

        """
        pass

    def data(self, byte_end, byte_begin=None, type=int, endian='little') -> int | str:
        """

retrieve the field in the buffer



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. Included. Default: None, means same as byte_end

    type (type): the type of the field to be converted (e.g. int, str). Default: int

    endian (str): the endian. Default: little.



Returns:

    (int or str): the data in the specified field

        """
        pass

    @property
    def data_head(self):
        """  display the first 16-byte of the buffer  """
        pass

    @property
    def data_tail(self):
        """  display the last 16-byte of the buffer  """
        pass

    def diff(self, buf2):
        """

generate diff html output 

        """
        pass

    def distance(self, buf2) -> int:
        """

distance with another buffer 

        """
        pass

    def dump(self, size=None) -> str:
        """

get the buffer data with a human friendly output



Args:

    size (int): the size of the buffer to print. Default: None, to print the whole buffer

        """
        pass

    def fill_pattern(self, pvalue=0, ptype=0):
        """

fill pattern data into the buffer, following ptype/pvalue definition

        

        """
        pass

    def match(self, file_ptn=None) -> Buffer:
        """

find the best match pattern from the pattern file 

        """
        pass

    @property
    def name(self):
        """ Buffer.name: str """
        pass

    @property
    def offset(self):
        """ Buffer.offset: int """
        pass

    @property
    def phys_addr(self):
        """  physical address of the buffer starting from the offset  """
        pass

    def read_16byte(self, offset) -> tuple[int]:
        """

read data from memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

    def set_controller_list(self, *cntlid_list):
        """

set controller id list in buffer



Args:

    cntlid_list (list of int): the list of controller id

        """
        pass

    def set_copy_range(self, index, lba, lba_count, format=0, storage_reference_tag=0, app_tag=0, app_tag_mask=0):
        """

set copy command ranges in the buffer



Args:

    index (int): the index of the copy range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range. 1-based.

    format (int): the format of the copy command range

        """
        pass

    def set_dsm_range(self, index, lba, lba_count, attr=0):
        """

set DSM command ranges in the buffer



Args:

    index (int): the index of the dsm range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range, 1-based.

    attr (int): context attributes of the range. Default: 0

        """
        pass

    @property
    def sgl(self):
        """ Buffer.sgl: bool """
        pass

    @property
    def size(self):
        """ Buffer.size: int """
        pass

    def write_16byte(self, offset, dword0, dword1, dword2, dword3):
        """

write data to memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

class PRP:
    def __init__() -> PRP:
        """  PRP data structure     """
        pass

    def crc8(self):
        """

get crc8 of the buffer 

        """
        pass

    def data(self, byte_end, byte_begin=None, type=int, endian='little') -> int | str:
        """

retrieve the field in the buffer



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. Included. Default: None, means same as byte_end

    type (type): the type of the field to be converted (e.g. int, str). Default: int

    endian (str): the endian. Default: little.



Returns:

    (int or str): the data in the specified field

        """
        pass

    @property
    def data_head(self):
        """  display the first 16-byte of the buffer  """
        pass

    @property
    def data_tail(self):
        """  display the last 16-byte of the buffer  """
        pass

    def diff(self, buf2):
        """

generate diff html output 

        """
        pass

    def distance(self, buf2) -> int:
        """

distance with another buffer 

        """
        pass

    def dump(self, size=None) -> str:
        """

get the buffer data with a human friendly output



Args:

    size (int): the size of the buffer to print. Default: None, to print the whole buffer

        """
        pass

    def fill_pattern(self, pvalue=0, ptype=0):
        """

fill pattern data into the buffer, following ptype/pvalue definition

        

        """
        pass

    def match(self, file_ptn=None) -> Buffer:
        """

find the best match pattern from the pattern file 

        """
        pass

    @property
    def name(self):
        """ Buffer.name: str """
        pass

    @property
    def offset(self):
        """ Buffer.offset: int """
        pass

    @property
    def phys_addr(self):
        """  physical address of the buffer starting from the offset  """
        pass

    def read_16byte(self, offset) -> tuple[int]:
        """

read data from memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

    def set_controller_list(self, *cntlid_list):
        """

set controller id list in buffer



Args:

    cntlid_list (list of int): the list of controller id

        """
        pass

    def set_copy_range(self, index, lba, lba_count, format=0, storage_reference_tag=0, app_tag=0, app_tag_mask=0):
        """

set copy command ranges in the buffer



Args:

    index (int): the index of the copy range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range. 1-based.

    format (int): the format of the copy command range

        """
        pass

    def set_dsm_range(self, index, lba, lba_count, attr=0):
        """

set DSM command ranges in the buffer



Args:

    index (int): the index of the dsm range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range, 1-based.

    attr (int): context attributes of the range. Default: 0

        """
        pass

    @property
    def sgl(self):
        """ Buffer.sgl: bool """
        pass

    @property
    def size(self):
        """ Buffer.size: int """
        pass

    def write_16byte(self, offset, dword0, dword1, dword2, dword3):
        """

write data to memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

class PRPList:
    def __init__() -> PRPList:
        """  PRPList data structure     """
        pass

    def crc8(self):
        """

get crc8 of the buffer 

        """
        pass

    def data(self, byte_end, byte_begin=None, type=int, endian='little') -> int | str:
        """

retrieve the field in the buffer



Args:

    byte_end (int): the end byte number of this field, which is specified in NVMe spec. Included.

    byte_begin (int): the begin byte number of this field, which is specified in NVMe spec. Included. Default: None, means same as byte_end

    type (type): the type of the field to be converted (e.g. int, str). Default: int

    endian (str): the endian. Default: little.



Returns:

    (int or str): the data in the specified field

        """
        pass

    @property
    def data_head(self):
        """  display the first 16-byte of the buffer  """
        pass

    @property
    def data_tail(self):
        """  display the last 16-byte of the buffer  """
        pass

    def diff(self, buf2):
        """

generate diff html output 

        """
        pass

    def distance(self, buf2) -> int:
        """

distance with another buffer 

        """
        pass

    def dump(self, size=None) -> str:
        """

get the buffer data with a human friendly output



Args:

    size (int): the size of the buffer to print. Default: None, to print the whole buffer

        """
        pass

    def fill_pattern(self, pvalue=0, ptype=0):
        """

fill pattern data into the buffer, following ptype/pvalue definition

        

        """
        pass

    def find_buffer_by_offset(self, offset, start):
        """

find the buffer of the non-contiguous queue contains the offset

        """
        pass

    def match(self, file_ptn=None) -> Buffer:
        """

find the best match pattern from the pattern file 

        """
        pass

    @property
    def name(self):
        """ Buffer.name: str """
        pass

    @property
    def offset(self):
        """ Buffer.offset: int """
        pass

    @property
    def phys_addr(self):
        """  physical address of the buffer starting from the offset  """
        pass

    def read_16byte(self, offset) -> tuple[int]:
        """

read data from memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

    def set_controller_list(self, *cntlid_list):
        """

set controller id list in buffer



Args:

    cntlid_list (list of int): the list of controller id

        """
        pass

    def set_copy_range(self, index, lba, lba_count, format=0, storage_reference_tag=0, app_tag=0, app_tag_mask=0):
        """

set copy command ranges in the buffer



Args:

    index (int): the index of the copy range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range. 1-based.

    format (int): the format of the copy command range

        """
        pass

    def set_dsm_range(self, index, lba, lba_count, attr=0):
        """

set DSM command ranges in the buffer



Args:

    index (int): the index of the dsm range to set

    lba (int): the start lba of the range

    lba_count (int): the lba count of the range, 1-based.

    attr (int): context attributes of the range. Default: 0

        """
        pass

    @property
    def sgl(self):
        """ Buffer.sgl: bool """
        pass

    @property
    def size(self):
        """ Buffer.size: int """
        pass

    def write_16byte(self, offset, dword0, dword1, dword2, dword3):
        """

write data to memory with better performance



Args:

    offset (int): dword offset in the buffer

        """
        pass

class NvmeShutdownStatusTimeoutError:
    def __init__() -> NvmeShutdownStatusTimeoutError:
        """ None    """
        pass

class NvmeEnumerateError:
    def __init__() -> NvmeEnumerateError:
        """ None    """
        pass

class NvmeDeletionError:
    def __init__() -> NvmeDeletionError:
        """ None    """
        pass

class QpairCreationError:
    def __init__() -> QpairCreationError:
        """ None    """
        pass

class QpairDeletionError:
    def __init__() -> QpairDeletionError:
        """ None    """
        pass

class NamespaceCreationError:
    def __init__() -> NamespaceCreationError:
        """ None    """
        pass

class NamespaceDeletionError:
    def __init__() -> NamespaceDeletionError:
        """ None    """
        pass

