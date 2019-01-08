# nvme
pynvme, a driver for NVMe SSD testing in Python3 scripts

Pynvme Driver is a python extension module. Users can operate NVMe SSD intuitively by Python scripts. It is designed for NVMe SSD testing with performance considered. With third-party tools, e.g. pycharm and pytest, Pynvme is a convinent and professional NVMe device test solution. It can test multiple NVMe DUT devices, operate most of the NVMe commands, support callback functions, and manage reset/power of NVMe devices. User needs root privilage to run SSDMeter.

Pynvme provides several classes to access and test NVMe devices:
1. Subsystem: controls the power and reset of NVMe subsystem
2. Pcie: accesses PCIe device's config space
3. Controller: accesses NVMe registers and operates admin commands
4. Namespace: abstracts NVMe namespace and operates NVM commands
5. Qpair: manages NVMe IO SQ/CQ. Admin SQ/CQ are managed by Controller
6. Buffer: allocates and manipulates the data buffer on host memory
7. IOWorker: reads and/or writes NVMe Namespace in seperated processors
Please use "help" to find more details of these classes.

Pynvme works on Linux, and uses SPDK as the NVMe driver. DPDK and SPDK are statically linked in the module's .so object file, so users do not need to setup SPDK develop environment. The host Linux OS image is installed in a SATA drive, because the kernel's NVMe drive will be unloaded by Pynvme during the test. Pynvme does write data to your NVMe devices, so it could corrupt your data in the device. Users have to provide correct BDF (Bus:Device.Function) address to initialize the controller of the DUT device.

Pynvme is easy to use, from simple operations to deliberated designed test scripts. User can leverage well developed tools and knowledges in Python community. Here are some Pynvme script examples.

Fetch the controller's identify data. Example:
```python
    >>> import nvme as d
    >>> nvme0 = d.Controller(b"01:00.0")  `initialize` NVMe controller with its PCIe BDF address
    >>> id_buf = d.Buffer(4096)  `allocate` the buffer
    >>> nvme0.identify(id_buf, nsid=0xffffffff, cns=1)  `read` namespace identify data into buffer
    >>> nvme0.waitdone()  `nvme` commands are executed asynchorously, so we have to
    >>> id_buf.dump()  `print` the whole buffer
```

Yet another hello world example of SPDK nvme driver. Example:
```python
    >>> import nvme as d
    >>> data_buf = d.Buffer(512)
    >>> data_buf[100:] = b'hello world'
    >>> nvme0 = d.Controller(b"01:00.0")
    >>> nvme0n1 = d.Namespace(nvme0, 1)
    >>> qpair = d.Qpair(nvme0, 16)  # create IO SQ/CQ pair, with 16 queue-depth
    >>> def write_cb(cdw0, status):  # command callback function
    >>>     nvme0n1.read(qpair, data_buf, 0, 1).waitdone()
    >>> nvme0n1.write(qpair, data_buf, 0, 1, cb=write_cb).waitdone()
    >>> qpair.cmdlog()  # print recently issued commands
    >>> assert data_buf[100:] = b'hello world'
```

Performance test, while monitoring the device temperature. Example:
```python
    >>> import nvme as d
    >>> nvme0 = d.Controller(b"01:00.0")
    >>> nvme0n1 = d.Namespace(nvme0, 1)
    >>> with nvme0n1.ioworker(lba_start = 0, io_size = 256, lba_align = 8,
                              lba_random = False,
                              region_start = 0, region_end = 100000,
                              read_percentage = 0,
                              iops = 0, io_count = 1000000, time = 0,
                              qprio = 0, qdepth = 16), \
             nvme0n1.ioworker(lba_start = 0, io_size = 7, lba_align = 11,
                              lba_random = False,
                              region_start = 0, region_end = 1000,
                              read_percentage = 0,
                              iops = 0, io_count = 100, time = 1000,
                              qprio = 0, qdepth = 64), \
             nvme0n1.ioworker(lba_start = 0, io_size = 8, lba_align = 64,
                              lba_random = False,
                              region_start = 10000, region_end = 1000000,
                              read_percentage = 67,
                              iops = 10000, io_count = 1000000, time = 1000,
                              qprio = 0, qdepth = 16), \
             nvme0n1.ioworker(lba_start = 0, io_size = 8, lba_align = 8,
                              lba_random = True,
                              region_start = 0, region_end = 0xffffffffffffffff,
                              read_percentage = 0,
                              iops = 10, io_count = 100, time = 0,
                              qprio = 0, qdepth = 16):
    >>>     import time
    >>>     import logging
    >>>     import pytemperature
    >>>     # monitor device temperature on high loading operations
    >>>     logpage_buf = d.Buffer(512)
    >>>     nvme0.getlogpage(2, logpage_buf, 512).waitdone()
    >>>     logging.info("current temperature: %d" % pytemperature.k2c(logpage_buf[50]&0xffff))
    >>>     time.sleep(5)
```

System Requirement:
1. Intel CPU with SSE4.2 instruction set
2. 8GB DRAM recommended, or more if the DUT capacity is larger
3. deep mode is supported in /sys/power/mem_sleep
3. Tested with Fedora 28 and Python 3.6
4. pytest is used as the test framework
5. security functions (e.g. TCG, pyrite) are not enabled

Pynvme v0.1.x is focused on mainstream client NVMe SSD, following NVMe spec v1.3c. Some features are NOT supported for now. We will continue to develop the features listed below to support more tests and devices in future. New requests and contributions are warmly welcomed.
1. Weighted Round Robin arbitration
2. SGL
3. multiple namespace management
4. Directive operations
5. sudden power cycle: shutdown while writing data
6. metadata and protect information
7. virtualization management
8. security send/receive and RPMB
9. boot partition
10. Management Interface
11. NVMe over fabrics
12. Open-channel SSD
13. Vendor Specific commands
14. platform compatibility

Pynvme writes and reads data in buffer to NVMe device LBA space. In order to verify the data integrity, it injects LBA address and version information into the write data buffer, and check with them after read completion. Furthermore, Pynvme computes and verifies CRC32 of each LBA on the fly. Both data buffer and LBA CRC32 are stored in host memory, so ECC memory are recommended if you are considering serious tests.

Buffer should be allocated for data commands, and held till that command is completed because the buffer is being used by NVMe device. Users need to pay more attention on the life scope of the buffer in Python test scripts.

NVMe commands are all asychronous. Test scripts can sync thourgh waitdone() method to make sure the command is completed. The method waitdone() polls command Completion Queues. When the optional callback function is provided in a command in Python scripts, the callback funciton is called when that command is completed. Callback functions are eventually called by waitdone(), and so do not call waitdone in callback function to avoid re-entry of waitdone functions, which requires a lock inside.

Pynvme traces recent thousands of commands in the cmdlog, as well as the completion entries. User can list cmdlog to find the commands issued in different command queues, and their timestamps.

The cost is high and unconvinent to send each read and write command in Python scripts. Pynvme provides the low-cost IOWorker to send IOs in different processores. IOWorker takes full use of multi-core to not only send read/write IO in high speed, but also verify the correctness of data on the fly. User can get IOWorker's test statistics through its close() method. Here is an example of reading 4K data randomly with the IOWorker.

Example:
```python
    >>> r = nvme0n1.ioworker(io_size = 8, lba_align = 8,
                             lba_random = True, qdepth = 16,
                             read_percentage = 100, time = 10).start().close()
    >>> print(r.io_count_read)
    >>> print(r.mseconds)
    >>> print("IOPS: %dK/s\n", r.io_count_read/r.mseconds)
```

The controller is not responsible for checking the LBA of a Read or Write command to ensure any type of ordering between commands (NVMe spec 1.3c, 6.3). It means conflicted read write operations on NVMe devices cannot predict the final data result, and thus hard to verify data correctness. For test scripts, one mitigation solution is separating read and write operations to differnt IOWorkers and different LBA regions, so it can be avoid to read and write same LBA at simultanously. For those read and write operations on same LBA region, scripts have to complete one before submitting the other.

Qpair instance is created based on Controller instance. So, user creates qpair after the controller. In the other side, user should free qpair before the controller. But without explict code, Python may not do the job in right order. One of the mitigation solution is pytest fixture scope. User can define Controller fixture as session scope and Qpair as function. In the situation, qpair is always deleted before the controller.

## Buffer
```python
Buffer(self, /, *args, **kwargs)
```
Buffer class allocated in DPDK memzone,so can be used by DMA. Data in buffer is clear to 0 in initialization.

Args:
    size (int): the size (in bytes) of the buffer
                default: 4096
    name (str): the name of the buffer
                default: 'buffer'

Examples:
```python
    >>> b = Buffer(1024, 'example')
    >>> b[0] = 0x5a
    >>> b[1:3] = [1, 2]
    >>> b[4:] = [10, 11, 12, 13]
    >>> b.dump(16)
    example
    00000000  5a 01 02 00 0a 0b 0c 0d  00 00 00 00 00 00 00 00   Z...............
    >>> b[:8:2]
    b'Z\x02\n\x0c'
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

## Controller
```python
Controller(self, /, *args, **kwargs)
```
Controller class. Prefer to use fixture "nvme0" in test scripts.

Args:
    bdf (bytes): the bus/device/function address of the DUT, example: b'01:00.0'.

Example:
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

## DotDict
```python
DotDict(self, *args, **kwargs)
```
utility class to access dict members by . operation
## Namespace
```python
Namespace(self, /, *args, **kwargs)
```
Namespace class. Prefer to use fixture "nvme0n1" in test scripts.

Args:
    nvme (Controller): controller where to create the queue
    nsid (int): nsid of the namespace

## Pcie
```python
Pcie(self, /, *args, **kwargs)
```
Pcie class. Prefer to use fixture "pcie" in test scripts

Args:
    nvme (Controller): the nvme controller object of that subsystem

## Qpair
```python
Qpair(self, /, *args, **kwargs)
```
Qpair class. IO SQ and CQ are combinded as qpairs.

Args:
    nvme (Controller): controller where to create the queue
    depth (int): SQ/CQ queue depth
    prio (int): when Weighted Round Robin is enabled, specify SQ priority here

## Subsystem
```python
Subsystem(self, /, *args, **kwargs)
```
Subsystem class. Prefer to use fixture "subsystem" in test scripts.

Args:
    nvme (Controller): the nvme controller object of that subsystem

