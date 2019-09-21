.. role:: raw-html-m2r(raw)
   :format: html

pynvme
======

test NVMe devices in Python. [https://github.com/cranechu/pynvme]


.. image:: https://img.shields.io/gitlab/pipeline/cranechu/pynvme.svg
   :target: https://gitlab.com/cranechu/pynvme/pipelines
   :alt: Status


.. image:: https://img.shields.io/github/license/cranechu/pynvme.svg
   :target: https://github.com/cranechu/pynvme/blob/master/LICENSE
   :alt: License


.. image:: https://img.shields.io/github/release/cranechu/pynvme.svg
   :target: https://github.com/cranechu/pynvme/releases
   :alt: Release


The pynvme is a python extension module. Users can operate NVMe SSD intuitively in Python scripts. It is designed for NVMe SSD testing with performance considered. Integrated with third-party tools, vscode and pytest, pynvme provides a convenient and professional solution to test NVMe devices.

The pynvme wraps SPDK NVMe driver in a Python extension, with abstracted classes, e.g. Controller, Namespace, Qpair, Buffer, and IOWorker. With pynvme, users can operate NVMe devices intuitively, including:


#. access PCI configuration space
#. access NVMe registers in BAR space
#. send any NVMe admin/IO commands
#. callback functions are supported
#. MSIx interrupt is supported
#. transparent checksum verification for each LBA
#. IOWorker generates high-performance IO
#. integrated with pytest
#. integrated with VSCode
#. test multiple controllers, namespaces and qpairs simultaneously
#. test NVMe over TCP targets

Before moving forward, check and backup your data in the NVMe SSD to be tested. It is always recommended to attach just one piece of NVMe SSD in your system to avoid mistakes.

Install
=======

Users can install and use pynvme in commodity computers.

System Requirement
------------------


#. CPU: x86_64.
#. OS: Linux.
#. Memory: 4GB or larger.
#. SATA: install OS and pynvme in a SATA drive.
#. NVMe: NVMe SSD is the device to be tested. Backup your data!
#. Python3: Python2 is not supported.
#. sudo privilege is required.
#. RAID mode (Intel® RST): should be disabled in BIOS.
#. Secure boot: should be disabled in BIOS.

Source Code
-----------

Fetch pynvme source code from GitHub, and simply run *install.sh* to build pynvme. *install.sh* generates the pynvme python package *nvme.cpython-37m-x86_64-linux-gnu.so*.

.. code-block:: shell

   git clone https://github.com/cranechu/pynvme
   cd pynvme
   ./install.sh

Now, it is ready to `start vscode <#vscode>`_. Or, you can continue to refer to detailed installation instructions below.

Prerequisites
-------------

First, to fetch all required dependencies source code and packages.

.. code-block:: shell

   git submodule update --init --recursive
   sudo dnf install python3-pip -y # Ubuntu: sudo apt-get install python3-pip

Build
-----

Compile the SPDK, and then pynvme.

.. code-block:: shell

   cd spdk; ./configure --without-isal; cd ..   # configurate SPDK
   make spdk                                    # compile SPDK
   make                                         # compile pynvme

Now, you can find the generated binary file like: nvme.cpython-37m-x86_64-linux-gnu.so

Test
----

Setup SPDK runtime environment to remove kernel NVMe driver and enable SPDK NVMe driver. Now, we can run tests!

.. code-block:: shell

   # backup your data in NVMe SSD before testing
   make setup
   make test
   make test TESTS=scripts
   make test TESTS=scripts/demo_test.py
   make test TESTS=scripts/utility_test.py::test_download_firmware

By default, it runs tests in driver_test.py. However, these are tests of pynvme itself, instead of SSD drives. Your DUT drive may fail in some test cases. Please add your tests in *scripts* directory.
Test logs are saved in file *test.log*. When you submit issues, please kindly attach this test.log file.

After test, you may wish to bring kernel NVMe driver back like this:

.. code-block:: shell

   make reset

User can find pynvme documents in README.md, or use help() in python:

.. code-block:: shell

   sudo python3 -c "import nvme; help(nvme)"  # press q to quit

VSCode
======

The pynvme works with VSCode! And pytest too!


#. 
   First of all, install vscode here: https://code.visualstudio.com/

#. 
   Root user is not recommended in vscode, so just use your ordinary non-root user. It is required to configurate the user account to run sudo without a password.

   .. code-block:: shell

      sudo visudo

#. 
   In order to monitor qpairs status and cmdlog along the progress of testing, user can install vscode extension pynvme-console. The extension provides DUT status and cmdlogs in VSCode UI.

   .. code-block:: shell

      code --install-extension pynvme-console-1.x.x.vsix

#. 
   Before start vscode, modify .vscode/settings.json with the correct pcie address (bus:device.function, which can be found by lspci shell command) of your DUT device.

   .. code-block:: shell

      lspci
      # 01:00.0 Non-Volatile memory controller: Lite-On Technology Corporation Device 2300 (rev 01)

#. 
   Then in pynvme folder, we can start vscode to edit, debug and run scripts:

   .. code-block:: shell

      make setup; code .  # make sure to enable SPDK nvme driver before starting vscode

#. 
   Users can add their own script files under scripts directory. Import following packages in new test script files.

   .. code-block:: python

   import pytest
   import logging

import nvme as d    # import pynvme's python package


   7. Now, we can debug and run test scripts in VSCode!
   ![](./vscode.png)
   - A. Activity Bar: you can select the last Test icon for pytest and pynvme extentions.
   - B. pytest panel: collects all test files and cases in scripts directory.
   - C. pynvme panel: displays all active qpairs in all controllers. Click qpair to open or refresh its cmdlog viewer.
   - D. editor: edit test scripts here.
   - E. cmdlog viewer: displays the latest 128 command and completion dwords in one qpair.
   - F. log viewer: displays pytest log.

   VSCode is convenient and powerful, but it consumes a lot of resources. So, for formal performance tests and regular CI tests, it is recommended to run tests in command line, by *make test*.


Tutorial
========

   After installation, pynvme generates the binary extension which can be import-ed in python scripts. Example:

   .. code-block:: python

   import nvme as d

   nvme0 = d.Controller(b"01:00.0")  # initialize NVMe controller with its PCIe BDF address
   id_buf = d.Buffer(4096)  # allocate the buffer
   nvme0.identify(id_buf, nsid=0xffffffff, cns=1)  # read namespace identify data into buffer
   nvme0.waitdone()  # nvme commands are executed asynchronously, so we have to wait the completion before access the id_buf.
   print(id_buf.dump())   # print the whole buffer

In order to write test scripts more efficently, pynvme provides pytest fixtures. We can write more in intuitive test scripts. Example

.. code-block:: python

   import pytest
   import nvme as d

   def test_dump_namespace_identify_data(nvme0):
       id_buf = d.Buffer()
       nvme0.identify(id_buf, nsid=0xffff_ffff, cns=1).waitdone()
       print(id_buf.dump())

The pytest can collect and execute these test scripts in both command line and IDE (e.g. VSCode). Example:

.. code-block:: shell

   sudo python3 -m pytest test_file_name.py::test_function_name --pciaddr=BB:DD.FF  # find the BDF address by lspci

By default, pytest captures all outputs, and only test results are printed. By adding the option "-s" in the above command line, pytest will also print scripts and pynvme's messages.Please refer to `pytest documents <https://docs.pytest.org/en/latest/contents.html>`_ for more instructions.

To make the simplisity a step further, pynvme provides more python facilities. If the optional type hint is given to the fixtures, VSCode can give you more help. Example:

.. code-block:: python

   import pytest
   import nvme as d

   def test_namespace_identify_size(nvme0n1: d.Namespace):
       assert nvme0n1.id_data(7, 0) != 0

Callback functions are supported. If available, the callback function is called when the command completes. Example:

.. code-block:: python

   import pytest
   import nvme as d

   def test_hello_world(nvme0, nvme0n1:d.Namespace):
       read_buf = d.Buffer(512)
       data_buf = d.Buffer(512)
       data_buf[10:21] = b'hello world'
       qpair = d.Qpair(nvme0, 16)  # create IO SQ/CQ pair, with 16 queue-depth
       assert read_buf[10:21] != b'hello world'

       # command callback function
       # NOTICE: status1 is a 16-bit integer including the phase bit!
       def write_cb(cdw0, status1):
           nvme0n1.read(qpair, read_buf, 0, 1)
       nvme0n1.write(qpair, data_buf, 0, 1, cb=write_cb)
       qpair.waitdone(2)
       assert read_buf[10:21] == b'hello world'

The pynvme can send any kinds of commands, even invalid one. Example:

.. code-block:: python

   import pytest

   def test_invalid_io_command_0xff(nvme0n1):
       q = d.Qpair(nvme0, 8)
       with pytest.warns(UserWarning, match="ERROR status: 00/01"):
           nvme0n1.send_cmd(0xff, q, nsid=1).waitdone()

The performance is low to send read write IO one by one in python, so pynvme provides IOWorker. IOWorker sends IO in a separated process, so we can send other admin commands simultaneously. Example:

.. code-block:: python

   import time
   import pytest
   from pytemperature import k2c

   def test_ioworker_with_temperature(nvme0, nvme0n1):
       smart_log = d.Buffer(512, "smart log page")
       with nvme0n1.ioworker(io_size=8, lba_align=16,
                             lba_random=True, qdepth=16,
                             read_percentage=0, time=30):
           # run ioworker for 30 seconds, while monitoring temperature for 40 seconds
           for i in range(40):
               nvme0.getlogpage(0x02, smart_log, 512).waitdone()
               ktemp = smart_log.data(2, 1)
               logging.info("temperature: %0.2f degreeC" % k2c(ktemp))
               time.sleep(1)

For more examples of pynvme test scripts, please refer to `driver_test.py <https://github.com/cranechu/pynvme/blob/master/driver_test.py>`_\ , `demo_test.py <https://github.com/cranechu/pynvme/blob/master/scripts/demo_test.py>`_\ , and a `presentation <https://raw.githubusercontent.com/cranechu/pynvme/master/doc/pynvme_introduction.pdf>`_.

Features
========

Pynvme writes and reads data in buffer to NVMe device LBA space. In order to verify the data integrity, it injects LBA address and version information into the write data buffer, and check with them after read completion. Furthermore, Pynvme computes and verifies CRC32 of each LBA on the fly. Both data buffer and LBA CRC32 are stored in host memory, so ECC memory are recommended if you are considering serious tests.

Buffer should be allocated for data commands, and held till that command is completed because the buffer is being used by NVMe device. Users need to pay more attention on the life scope of the buffer in Python test scripts.

NVMe commands are all asynchronous. Test scripts can sync through waitdone() method to make sure the command is completed. The method waitdone() polls command Completion Queues. When the optional callback function is provided in a command in python scripts, the callback function is called when that command is completed in waitdone(). The command timeout limit of pynvme is 5 seconds.

Pynvme driver provides two arguments to python callback functions: cdw0 of the Completion Queue Entry, and the status. The argument status includes both Phase Tag and Status Field.

Pynvme traces recent thousands of commands in the cmdlog, as well as the completion entries. The cmdlog traces each qpair's commands and status. Pynvme supports up to 16 qpairs (including the admin qpair of the controller). Users can list cmdlog of each qpair to find the commands issued in different command queues.

The cost is high and inconvenient to send each read and write command in Python scripts. Pynvme provides the low-cost IOWorker to send IOs in different processes. IOWorker takes full use of multi-core to not only send read/write IO in high speed, but also verify the correctness of data on the fly. User can get IOWorker's test statistics through its close() method. Here is an example of reading 4K data randomly with the IOWorker.

Example:

.. code-block:: python

       >>> r = nvme0n1.ioworker(io_size = 8, lba_align = 8,
                                lba_random = True, qdepth = 16,
                                read_percentage = 100, time = 10).start().close()
       >>> print(r.io_count_read)
       >>> print(r.mseconds)
       >>> print("IOPS: %dK/s\n", r.io_count_read/r.mseconds)

The controller is not responsible for checking the LBA of a Read or Write command to ensure any type of ordering between commands (NVMe spec 1.3c, 6.3). It means conflicted read write operations on NVMe devices cannot predict the final data result, and thus hard to verify data correctness. Similarly, after writing of multiple IOWorkers in the same LBA region, the subsequent read does not know the latest data content. As a mitigation solution, we suggest to separate read and write operations to different IOWorkers and different LBA regions in test scripts, so it can be avoid to read and write same LBA at simultaneously. For those read and write operations on same LBA region, scripts have to complete one before submitting the other. Test scripts can disable or enable inline verification of read by function config(). By default, it is disabled.

Qpair instance is created based on Controller instance. So, user creates qpair after the controller. In the other side, user should free qpair before the controller. But without explicit code, Python may not do the job in right order. One of the mitigation solution is pytest fixture scope. User can define Controller fixture as session scope and Qpair as function. In the situation, qpair is always deleted before the controller. Admin qpair is managed by controller, so users do not need to create the admin qpair.

Files
=====

Here is a brief introduction on source code files.

.. list-table::
   :header-rows: 1

   * - files
     - notes
   * - spdk
     - pynvme is built on SPDK
   * - driver_wrap.pyx
     - pynvme uses cython to bind python and C. All python classes are defined here.
   * - cdriver.pxd
     - interface between python and C
   * - driver.h
     - interface of C
   * - driver.c
     - the core part of pynvme, which extends SPDK for test purpose
   * - setup.py
     - cython configuration for compile
   * - Makefile
     - it is a part of SPDK makefiles
   * - driver_test.py
     - pytest cases for pynvme test. Users can develop more test cases for their NVMe devices.
   * - conftest.py
     - predefined pytest fixtures. Find more details below.
   * - pytest.ini
     - pytest runtime configuration
   * - install.sh
     - build pynvme for the first time


Fixtures
========

Pynvme uses pytest to test it self. Users can also use pytest as the test framework to test their NVMe devices. Pytest's fixture is a powerful way to create and free resources in the test.

.. list-table::
   :header-rows: 1

   * - fixture
     - scope
     - notes
   * - pciaddr
     - session
     - PCIe BDF address of the DUT, pass in by argument --pciaddr
   * - pcie
     - session
     - the object of the PCIe device.
   * - nvme0
     - session
     - the object of NVMe controller
   * - nvme0n1
     - session
     - the object of first Namespace of the controller
   * - verify
     - function
     - declare this fixture in test cases where data crc is to be verified.


Debug
=====


#. assert: it is recommended to compile SPDK with --enable-debug.
#. log: users can change log levels for driver and scripts. All logs are captured/hidden by pytest in default. Please use argument "-s" to print logs in test time.

   #. driver: spdk_log_set_print_level in driver.c, for SPDK related logs
   #. scripts: log_cli_level in pytest.ini, for python/pytest scripts

#. gdb: when driver crashes or misbehaviours, use can collect debug information through gdb.

   #. core dump: sudo coredumpctl debug
   #. generate core dump in dead loop: CTRL-\
   #. test within gdb: sudo gdb --args python3 -m pytest --color=yes --pciaddr=01:00.0 "driver_test.py::test_create_device"

If you meet any issue, or have any suggestions, please report them to `Issues <https://github.com/cranechu/pynvme/issues>`_. They are warmly welcome.

Classes
=======

Buffer
------

.. code-block:: python

   Buffer(self, /, *args, **kwargs)

Buffer class allocated in DPDK memzone,so can be used by DMA. Data in buffer is clear to 0 in initialization.

**Attributes**


* `size (int)`: the size (in bytes) of the buffer. Default: 4096
* `name (str)`: the name of the buffer. Default: 'buffer'
* `pvalue (int)`: data pattern value. Default: 0
* ``Different pattern type has different value definition``\ :
* `0`: 1-bit pattern: 0 for all-zero data, 1 for all-one data
* `32`: 32-bit pattern: 32-bit value of the pattern
* `0xbeef`: random data: random data compression percentage rate
* ``else``\ : not supported
* `ptype (int)`: data pattern type. Default: 0
* ``0``\ : 1-bit pattern
* ``32``\ : 32-bit pattern
* ``0xbeef``\ : random data
* 
  ``else``\ : not supported

* 
  ``Examples``\ :

  .. code-block:: python

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

data
^^^^

.. code-block:: python

   Buffer.data(self, byte_end, byte_begin, type)

get field in the buffer. Little endian for integers.

**Attributes**


* ``byte_end (int)``\ : the end byte number of this field, which is specified in NVMe spec. Included.
* `byte_begin (int)`: the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* `type (type)`: the type of the field. It should be int or str. Default: int, convert to integer python object

**Returns**

``(int or str)``\ : the data in the specified field

dump
^^^^

.. code-block:: python

   Buffer.dump(self, size)

get the buffer content

**Attributes**


* `size`: the size of the buffer to print,. Default: None, means to print the whole buffer

set_dsm_range
^^^^^^^^^^^^^

.. code-block:: python

   Buffer.set_dsm_range(self, index, lba, lba_count)

set dsm ranges in the buffer, for dsm/deallocation (a.ka trim) commands

**Attributes**


* ``index (int)``\ : the index of the dsm range to set
* ``lba (int)``\ : the start lba of the range
* ``lba_count (int)``\ : the lba count of the range

config
------

.. code-block:: python

   config(verify, fua_read=False, fua_write=False)

config driver global setting

**Attributes**


* ``verify (bool)``\ : enable inline checksum verification of read
* `fua_read (bool)`: enable FUA of read. Default: False
* `fua_write (bool)`: enable FUA of write. Default: False

**Returns**

.. code-block::

   None


Controller
----------

.. code-block:: python

   Controller(self, /, *args, **kwargs)

Controller class. Prefer to use fixture "nvme0" in test scripts.

**Attributes**


* `addr (bytes)`: the bus/device/function address of the DUT, for example:
* 
  ``b'01``\ :00.0' (PCIe BDF address);

  .. code-block::

                 b'127.0.0.1' (TCP IP address).

* 
  ``Example``\ :

  .. code-block:: python

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

abort
^^^^^

.. code-block:: python

   Controller.abort(self, cid, sqid, cb)

abort admin commands

**Attributes**


* ``cid (int)``\ : command id of the command to be aborted
* `sqid (int)`: sq id of the command to be aborted. Default: 0, to abort the admin command
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


aer
^^^

.. code-block:: python

   Controller.aer(self, cb)

asynchorous event request admin command.

Not suggested to use this command in scripts because driver manages to send and monitor aer commands. Scripts should register an aer callback function if it wants to handle aer, and use the fixture aer.

**Attributes**


* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


cap
^^^

64-bit CAP register of NVMe

cmdlog
^^^^^^

.. code-block:: python

   Controller.cmdlog(self, count)

print recent commands and their completions.

**Attributes**


* `count (int)`: the number of commands to print. Default: 0, to print the whole cmdlog

cmdname
^^^^^^^

.. code-block:: python

   Controller.cmdname(self, opcode)

get the name of the admin command

**Attributes**


* ``opcode (int)``\ : the opcode of the admin command

**Returns**

``(str)``\ : the command name

disable_hmb
^^^^^^^^^^^

.. code-block:: python

   Controller.disable_hmb(self)

disable HMB function

downfw
^^^^^^

.. code-block:: python

   Controller.downfw(self, filename, slot, action)

firmware download utility: by 4K, and activate in next reset

**Attributes**


* ``filename (str)``\ : the pathname of the firmware binary file to download
* `slot (int)`: firmware slot field in the command. Default: 0, decided by device
* `cb (function)`: callback function called at completion. Default: None

**Returns**

dst
^^^

.. code-block:: python

   Controller.dst(self, stc, nsid, cb)

device self test (DST) admin command

**Attributes**


* ``stc (int)``\ : selftest code (stc) field in the command
* `nsid (int)`: nsid field in the command. Default: 0xffffffff
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


enable_hmb
^^^^^^^^^^

.. code-block:: python

   Controller.enable_hmb(self)

enable HMB function

format
^^^^^^

.. code-block:: python

   Controller.format(self, lbaf, ses, nsid, cb)

format admin command

**Attributes**


* `lbaf (int)`: lbaf (lba format) field in the command. Default: 0
* `ses (int)`: ses field in the command. Default: 0, no secure erase
* `nsid (int)`: nsid field in the command. Default: 1
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


fw_commit
^^^^^^^^^

.. code-block:: python

   Controller.fw_commit(self, slot, action, cb)

firmware commit admin command

**Attributes**


* ``slot (int)``\ : firmware slot field in the command
* ``action (int)``\ : action field in the command
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


fw_download
^^^^^^^^^^^

.. code-block:: python

   Controller.fw_download(self, buf, offset, size, cb)

firmware download admin command

**Attributes**


* ``buf (Buffer)``\ : the buffer to hold the firmware data
* ``offset (int)``\ : offset field in the command
* `size (int)`: size field in the command. Default: None, means the size of the buffer
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


getfeatures
^^^^^^^^^^^

.. code-block:: python

   Controller.getfeatures(self, fid, cdw11, cdw12, cdw13, cdw14, cdw15, sel, buf, cb)

getfeatures admin command

**Attributes**


* ``fid (int)``\ : feature id
* `cdw11 (int)`: cdw11 in the command. Default: 0
* `sel (int)`: sel field in the command. Default: 0
* `buf (Buffer)`: the buffer to hold the feature data. Default: None
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


getlogpage
^^^^^^^^^^

.. code-block:: python

   Controller.getlogpage(self, lid, buf, size, offset, nsid, cb)

getlogpage admin command

**Attributes**


* ``lid (int)``\ : Log Page Identifier
* ``buf (Buffer)``\ : buffer to hold the log page
* `size (int)`: size (in byte) of data to get from the log page,. Default: None, means the size is the same of the buffer
* ``offset (int)``\ : the location within a log page
* `nsid (int)`: nsid field in the command. Default: 0xffffffff
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


id_data
^^^^^^^

.. code-block:: python

   Controller.id_data(self, byte_end, byte_begin, type, nsid, cns)

get field in controller identify data

**Attributes**


* ``byte_end (int)``\ : the end byte number of this field, which is specified in NVMe spec. Included.
* `byte_begin (int)`: the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* `type (type)`: the type of the field. It should be int or str. Default: int, convert to integer python object

**Returns**

``(int or str)``\ : the data in the specified field

identify
^^^^^^^^

.. code-block:: python

   Controller.identify(self, buf, nsid, cns, cb)

identify admin command

**Attributes**


* ``buf (Buffer)``\ : the buffer to hold the identify data
* `nsid (int)`: nsid field in the command. Default: 0
* `cns (int)`: cns field in the command. Default: 1
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


mdts
^^^^

max data transfer size

register_aer_cb
^^^^^^^^^^^^^^^

.. code-block:: python

   Controller.register_aer_cb(self, func)

register aer callback to driver.

It is recommended to use fixture aer(func) in pytest scripts.
When aer is triggered, the python callback function will
be called. It is unregistered by aer fixture when test finish.

**Attributes**


* ``func (function)``\ : callback function called at aer completion

reset
^^^^^

.. code-block:: python

   Controller.reset(self)

controller reset: cc.en 1 => 0 => 1

**Notices**

.. code-block::

   Test scripts should delete all io qpairs before reset!


sanitize
^^^^^^^^

.. code-block:: python

   Controller.sanitize(self, option, pattern, cb)

sanitize admin command

**Attributes**


* ``option (int)``\ : sanitize option field in the command
* `pattern (int)`: pattern field in the command for overwrite method. Default: 0x5aa5a55a
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


send_cmd
^^^^^^^^

.. code-block:: python

   Controller.send_cmd(self, opcode, buf, nsid, cdw10, cdw11, cdw12, cdw13, cdw14, cdw15, cb)

send generic admin commands.

This is a generic method. Scripts can use this method to send all kinds of commands, like Vendor Specific commands, and even not existed commands.

**Attributes**


* ``opcode (int)``\ : operate code of the command
* `buf (Buffer)`: buffer of the command. Default: None
* `nsid (int)`: nsid field of the command. Default: 0
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


setfeatures
^^^^^^^^^^^

.. code-block:: python

   Controller.setfeatures(self, fid, cdw11, cdw12, cdw13, cdw14, cdw15, sv, buf, cb)

setfeatures admin command

**Attributes**


* ``fid (int)``\ : feature id
* `cdw11 (int)`: cdw11 in the command. Default: 0
* `sv (int)`: sv field in the command. Default: 0
* `buf (Buffer)`: the buffer to hold the feature data. Default: None
* `cb (function)`: callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


supports
^^^^^^^^

.. code-block:: python

   Controller.supports(self, opcode)

check if the admin command is supported

**Attributes**


* ``opcode (int)``\ : the opcode of the admin command

**Returns**

``(bool)``\ : if the command is supported

timeout
^^^^^^^

timeout value of this controller in milli-seconds.

It is configurable by assigning new value in milli-seconds.

waitdone
^^^^^^^^

.. code-block:: python

   Controller.waitdone(self, expected)

sync until expected commands completion

**Attributes**


* `expected (int)`: expected commands to complete. Default: 1

**Notices**

.. code-block::

   Do not call this function in commands callback functions.


DotDict
-------

.. code-block:: python

   DotDict(self, *args, **kwargs)

utility class to access dict members by . operation

Namespace
---------

.. code-block:: python

   Namespace(self, /, *args, **kwargs)

Namespace class. Prefer to use fixture "nvme0n1" in test scripts.

**Attributes**


* ``nvme (Controller)``\ : controller where to create the queue
* ``nsid (int)``\ : nsid of the namespace

capacity
^^^^^^^^

bytes of namespace capacity

close
^^^^^

.. code-block:: python

   Namespace.close(self)

close namespace to release it resources in host memory.

Notice:
    Release resources explictly, del is not garentee to call **dealloc**.
    Fixture nvme0n1 uses this function, and prefer to use fixture in scripts, instead of calling this function directly.

cmdname
^^^^^^^

.. code-block:: python

   Namespace.cmdname(self, opcode)

get the name of the IO command

**Attributes**


* ``opcode (int)``\ : the opcode of the IO command

**Returns**

``(str)``\ : the command name

compare
^^^^^^^

.. code-block:: python

   Namespace.compare(self, qpair, buf, lba, lba_count, io_flags, cb)

compare IO command

**Attributes**


* ``qpair (Qpair)``\ : use the qpair to send this command
* ``buf (Buffer)``\ : the data buffer of the command, meta data is not supported.
* ``lba (int)``\ : the starting lba address, 64 bits
* `lba_count (int)`: the lba count of this command, 16 bits. Default: 1
* `io_flags (int)`: io flags defined in NVMe specification, 16 bits. Default: 0
* `cb (function)`: callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

**Notices**

.. code-block::

   buf cannot be released before the command completes.


dsm
^^^

.. code-block:: python

   Namespace.dsm(self, qpair, buf, range_count, attribute, cb)

data-set management IO command

**Attributes**


* ``qpair (Qpair)``\ : use the qpair to send this command
* ``buf (Buffer)``\ : the buffer of the lba ranges. Use buffer.set_dsm_range to prepare the buffer.
* ``range_count (int)``\ : the count of lba ranges in the buffer
* `attribute (int)`: attribute field of the command. Default: 0x4, as deallocation/trim
* `cb (function)`: callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

**Notices**

.. code-block::

   buf cannot be released before the command completes.


flush
^^^^^

.. code-block:: python

   Namespace.flush(self, qpair, cb)

flush IO command

**Attributes**


* ``qpair (Qpair)``\ : use the qpair to send this command
* `cb (function)`: callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

format
^^^^^^

.. code-block:: python

   Namespace.format(self, data_size, meta_size, ses)

change the format of this namespace

**Attributes**


* `data_size (int)`: data size. Default: 512
* `meta_size (int)`: meta data size. Default: 0
* `ses (int)`: ses field in the command. Default: 0, no secure erase

**Returns**

``(int or None)``\ : the lba format has the specified data size and meta data size

**Notices**

.. code-block::

   this facility not only sends format admin command, but also updates driver to activate new format immediately


get_lba_format
^^^^^^^^^^^^^^

.. code-block:: python

   Namespace.get_lba_format(self, data_size, meta_size)

find the lba format by its data size and meta data size

**Attributes**


* `data_size (int)`: data size. Default: 512
* `meta_size (int)`: meta data size. Default: 0

**Returns**

``(int or None)``\ : the lba format has the specified data size and meta data size

id_data
^^^^^^^

.. code-block:: python

   Namespace.id_data(self, byte_end, byte_begin, type)

get field in namespace identify data

**Attributes**


* ``byte_end (int)``\ : the end byte number of this field, which is specified in NVMe spec. Included.
* `byte_begin (int)`: the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* `type (type)`: the type of the field. It should be int or str. Default: int, convert to integer python object

**Returns**

``(int or str)``\ : the data in the specified field

ioworker
^^^^^^^^

.. code-block:: python

   Namespace.ioworker(self, io_size, lba_align, lba_random, read_percentage, time, qdepth, region_start, region_end, iops, io_count, lba_start, qprio, pvalue, ptype, output_io_per_second, output_percentile_latency)

workers sending different read/write IO on different CPU cores.

User defines IO characteristics in parameters, and then the ioworker
executes without user intervesion, until the test is completed. IOWorker
returns some statistic data at last.

User can start multiple IOWorkers, and they will be binded to different
CPU cores. Each IOWorker creates its own Qpair, so active IOWorker counts
is limited by maximum IO queues that DUT can provide.

Each ioworker can run upto 24 hours.

**Attributes**


* ``io_size (short)``\ : IO size, unit is LBA
* ``lba_align (short)``\ : IO alignment, unit is LBA
* ``lba_random (bool)``\ : True if sending IO with random starting LBA
* ``read_percentage (int)``\ : sending read/write mixed IO, 0 means write only, 100 means read only
* `time (int)`: specified maximum time of the IOWorker in seconds, up to 24*3600. Default:0, means no limit
* `qdepth (int)`: queue depth of the Qpair created by the IOWorker, up to 1024. Default: 64
* `region_start (long)`: sending IO in the specified LBA region, start. Default: 0
* `region_end (long)`: sending IO in the specified LBA region, end but not include. Default: 0xffff_ffff_ffff_ffff
* `iops (int)`: specified maximum IOPS. IOWorker throttles the sending IO speed. Default: 0, means no limit
* `io_count (long)`: specified maximum IO counts to send. Default: 0, means no limit
* `lba_start (long)`: the LBA address of the first command. Default: 0, means start from region_start
* `qprio (int)`: SQ priority. Default: 0, as Round Robin arbitration
* `pvalue (int)`: data pattern value. Refer to class Buffer. Default: 0
* `ptype (int)`: data pattern type. Refer to class Buffer. Default: 0
* `output_io_per_second (list)`: list to hold the output data of io_per_second. Default: None, not to collect the data
* `output_percentile_latency (dict)`: dict of io counter on different percentile latency. Dict key is the percentage, and the value is the latency in ms. Default: None, not to collect the data

**Returns**

.. code-block::

   ioworker object


nsid
^^^^

id of the namespace

read
^^^^

.. code-block:: python

   Namespace.read(self, qpair, buf, lba, lba_count, io_flags, cb)

read IO command

**Attributes**


* ``qpair (Qpair)``\ : use the qpair to send this command
* ``buf (Buffer)``\ : the data buffer of the command, meta data is not supported.
* ``lba (int)``\ : the starting lba address, 64 bits
* `lba_count (int)`: the lba count of this command, 16 bits. Default: 1
* `io_flags (int)`: io flags defined in NVMe specification, 16 bits. Default: 0
* `cb (function)`: callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the read command fails

**Notices**

.. code-block::

   buf cannot be released before the command completes.


send_cmd
^^^^^^^^

.. code-block:: python

   Namespace.send_cmd(self, opcode, qpair, buf, nsid, cdw10, cdw11, cdw12, cdw13, cdw14, cdw15, cb)

send generic IO commands.

This is a generic method. Scripts can use this method to send all kinds of commands, like Vendor Specific commands, and even not existed commands.

**Attributes**


* ``opcode (int)``\ : operate code of the command
* ``qpair (Qpair)``\ : qpair used to send this command
* `buf (Buffer)`: buffer of the command. Default: None
* `nsid (int)`: nsid field of the command. Default: 0
* `cb (function)`: callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

supports
^^^^^^^^

.. code-block:: python

   Namespace.supports(self, opcode)

check if the IO command is supported

**Attributes**


* ``opcode (int)``\ : the opcode of the IO command

**Returns**

``(bool)``\ : if the command is supported

write
^^^^^

.. code-block:: python

   Namespace.write(self, qpair, buf, lba, lba_count, io_flags, cb)

write IO command

**Attributes**


* ``qpair (Qpair)``\ : use the qpair to send this command
* ``buf (Buffer)``\ : the data buffer of the write command, meta data is not supported.
* ``lba (int)``\ : the starting lba address, 64 bits
* ``lba_count (int)``\ : the lba count of this command, 16 bits
* `io_flags (int)`: io flags defined in NVMe specification, 16 bits. Default: 0
* `cb (function)`: callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the write command fails

**Notices**

.. code-block::

   buf cannot be released before the command completes.


write_uncorrectable
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   Namespace.write_uncorrectable(self, qpair, lba, lba_count, cb)

write uncorrectable IO command

**Attributes**


* ``qpair (Qpair)``\ : use the qpair to send this command
* ``lba (int)``\ : the starting lba address, 64 bits
* `lba_count (int)`: the lba count of this command, 16 bits. Default: 1
* `cb (function)`: callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

write_zeroes
^^^^^^^^^^^^

.. code-block:: python

   Namespace.write_zeroes(self, qpair, lba, lba_count, io_flags, cb)

write zeroes IO command

**Attributes**


* ``qpair (Qpair)``\ : use the qpair to send this command
* ``lba (int)``\ : the starting lba address, 64 bits
* `lba_count (int)`: the lba count of this command, 16 bits. Default: 1
* `io_flags (int)`: io flags defined in NVMe specification, 16 bits. Default: 0
* `cb (function)`: callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

Pcie
----

.. code-block:: python

   Pcie(self, /, *args, **kwargs)

Pcie class. Prefer to use fixture "pcie" in test scripts

**Attributes**


* ``nvme (Controller)``\ : the nvme controller object of that subsystem

cap_offset
^^^^^^^^^^

.. code-block:: python

   Pcie.cap_offset(self, cap_id)

get the offset of a capability

**Attributes**


* ``cap_id (int)``\ : capability id

**Returns**

``(int)``\ : the offset of the register
    or None if the capability is not existed

register
^^^^^^^^

.. code-block:: python

   Pcie.register(self, offset, byte_count)

access registers in pcie config space, and get its integer value.

**Attributes**


* ``offset (int)``\ : the offset (in bytes) of the register in the config space
* ``byte_count (int)``\ : the size (in bytes) of the register

**Returns**

``(int)``\ : the value of the register

reset
^^^^^

.. code-block:: python

   Pcie.reset(self)

reset this pcie device

Qpair
-----

.. code-block:: python

   Qpair(self, /, *args, **kwargs)

Qpair class. IO SQ and CQ are combinded as qpairs.

**Attributes**


* ``nvme (Controller)``\ : controller where to create the queue
* ``depth (int)``\ : SQ/CQ queue depth
* ``prio (int)``\ : when Weighted Round Robin is enabled, specify SQ priority here

cmdlog
^^^^^^

.. code-block:: python

   Qpair.cmdlog(self, count)

print recent IO commands and their completions in this qpair.

**Attributes**


* `count (int)`: the number of commands to print. Default: 0, to print the whole cmdlog

waitdone
^^^^^^^^

.. code-block:: python

   Qpair.waitdone(self, expected)

sync until expected commands completion

**Attributes**


* `expected (int)`: expected commands to complete. Default: 1

**Notices**

.. code-block::

   Do not call this function in commands callback functions.


Subsystem
---------

.. code-block:: python

   Subsystem(self, /, *args, **kwargs)

Subsystem class. Prefer to use fixture "subsystem" in test scripts.

**Attributes**


* ``nvme (Controller)``\ : the nvme controller object of that subsystem

power_cycle
^^^^^^^^^^^

.. code-block:: python

   Subsystem.power_cycle(self, sec)

power off and on in seconds

**Attributes**


* ``sec (int)``\ : the seconds between power off and power on

reset
^^^^^

.. code-block:: python

   Subsystem.reset(self)

reset the nvme subsystem through register nssr.nssrc

shutdown_notify
^^^^^^^^^^^^^^^

.. code-block:: python

   Subsystem.shutdown_notify(self, abrupt)

notify nvme subsystem a shutdown event through register cc.chn

**Attributes**


* ``abrupt (bool)``\ : it will be an abrupt shutdown (return immediately) or clean shutdown (wait shutdown completely)
