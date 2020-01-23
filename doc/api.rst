
API
===

Buffer
------

.. code-block:: python

   Buffer(self, /, *args, **kwargs)

Buffer allocates memory in DPDK, so we can get its physical address for DMA. Data in buffer is clear to 0 in initialization.

**Parameters**


* **size (int)**\ : the size (in bytes) of the buffer. Default: 4096
* **name (str)**\ : the name of the buffer. Default: 'buffer'
* **pvalue (int)**\ : data pattern value. Default: 0
* **ptype (int)**\ : data pattern type. Default: 0

**data patterns**

.. code-block:: md

       |ptype    | pvalue                                                     |
       |---------|------------------------------------------------------------|
       |0        | 0 for all-zero data, 1 for all-one data                    |
       |32       | 32-bit value of the repeated data pattern                  |
       |0xbeef   | random data compressed rate (0: all 0; 100: fully random)  |
       |others   | not supported                                              |

**Examples**

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

**Parameters**


* **byte_end (int)**\ : the end byte number of this field, which is specified in NVMe spec. Included.
* **byte_begin (int)**\ : the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* **type (type)**\ : the type of the field. It should be int or str. Default: int, convert to integer python object

**Returns**

``(int or str)``\ : the data in the specified field

dump
^^^^

.. code-block:: python

   Buffer.dump(self, size)

get the buffer content

**Parameters**


* **size (int)**\ : the size of the buffer to print. Default: None, means to print the whole buffer

phys_addr
^^^^^^^^^

physical address of the buffer

set_dsm_range
^^^^^^^^^^^^^

.. code-block:: python

   Buffer.set_dsm_range(self, index, lba, lba_count)

set dsm ranges in the buffer, for dsm/deallocation (a.ka trim) commands

**Parameters**


* **index (int)**\ : the index of the dsm range to set
* **lba (int)**\ : the start lba of the range
* **lba_count (int)**\ : the lba count of the range

config
------

.. code-block:: python

   config(verify=None, ioworker_terminate=None)

config driver global setting

**Parameters**


* **verify (bool)**\ : enable inline checksum verification of read. Default: None, means no change
* **ioworker_terminate (bool)**\ : notify ioworker to terminate immediately. Default: None, means no change

Controller
----------

.. code-block:: python

   Controller(self, /, *args, **kwargs)

Controller class. Prefer to use fixture "nvme0" in test scripts.

**Parameters**


* **addr (bytes)**\ : the bus/device/function address of the DUT, for example:                       b'01:00.0' (PCIe BDF address),                        b'127.0.0.1' (TCP IP address).

**Example**

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

**Parameters**


* **cid (int)**\ : command id of the command to be aborted
* **sqid (int)**\ : sq id of the command to be aborted. Default: 0, to abort the admin command
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


aer
^^^

.. code-block:: python

   Controller.aer(self, cb)

asynchorous event request admin command.

Not suggested to use this command in scripts because driver manages to send and monitor aer commands. Scripts should register an aer callback function if it wants to handle aer, and use the fixture aer.

**Parameters**


* **cb (function)**\ : callback function called at completion. Default: None

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

**Parameters**


* **count (int)**\ : the number of commands to print. Default: 0, to print the whole cmdlog

cmdname
^^^^^^^

.. code-block:: python

   Controller.cmdname(self, opcode)

get the name of the admin command

**Parameters**


* **opcode (int)**\ : the opcode of the admin command

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

**Parameters**


* **filename (str)**\ : the pathname of the firmware binary file to download
* **slot (int)**\ : firmware slot field in the command. Default: 0, decided by device
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

dst
^^^

.. code-block:: python

   Controller.dst(self, stc, nsid, cb)

device self test (DST) admin command

**Parameters**


* **stc (int)**\ : selftest code (stc) field in the command
* **nsid (int)**\ : nsid field in the command. Default: 0xffffffff
* **cb (function)**\ : callback function called at completion. Default: None

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

Notice
    This Controller.format only send the admin command. Use Namespace.format to maintain pynvme internal data!

**Parameters**


* **lbaf (int)**\ : lbaf (lba format) field in the command. Default: 0
* **ses (int)**\ : ses field in the command. Default: 0, no secure erase
* **nsid (int)**\ : nsid field in the command. Default: 1
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


fw_commit
^^^^^^^^^

.. code-block:: python

   Controller.fw_commit(self, slot, action, cb)

firmware commit admin command

**Parameters**


* **slot (int)**\ : firmware slot field in the command
* **action (int)**\ : action field in the command
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


fw_download
^^^^^^^^^^^

.. code-block:: python

   Controller.fw_download(self, buf, offset, size, cb)

firmware download admin command

**Parameters**


* **buf (Buffer)**\ : the buffer to hold the firmware data
* **offset (int)**\ : offset field in the command
* **size (int)**\ : size field in the command. Default: None, means the size of the buffer
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


getfeatures
^^^^^^^^^^^

.. code-block:: python

   Controller.getfeatures(self, fid, cdw11, cdw12, cdw13, cdw14, cdw15, sel, buf, cb)

getfeatures admin command

**Parameters**


* **fid (int)**\ : feature id
* **cdw11 (int)**\ : cdw11 in the command. Default: 0
* **sel (int)**\ : sel field in the command. Default: 0
* **buf (Buffer)**\ : the buffer to hold the feature data. Default: None
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


getlogpage
^^^^^^^^^^

.. code-block:: python

   Controller.getlogpage(self, lid, buf, size, offset, nsid, cb)

getlogpage admin command

**Parameters**


* **lid (int)**\ : Log Page Identifier
* **buf (Buffer)**\ : buffer to hold the log page
* **size (int)**\ : size (in byte) of data to get from the log page,. Default: None, means the size is the same of the buffer
* **offset (int)**\ : the location within a log page
* **nsid (int)**\ : nsid field in the command. Default: 0xffffffff
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


id_data
^^^^^^^

.. code-block:: python

   Controller.id_data(self, byte_end, byte_begin, type, nsid, cns)

get field in controller identify data

**Parameters**


* **byte_end (int)**\ : the end byte number of this field, which is specified in NVMe spec. Included.
* **byte_begin (int)**\ : the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* **type (type)**\ : the type of the field. It should be int or str. Default: int, convert to integer python object

**Returns**

``(int or str)``\ : the data in the specified field

identify
^^^^^^^^

.. code-block:: python

   Controller.identify(self, buf, nsid, cns, cb)

identify admin command

**Parameters**


* **buf (Buffer)**\ : the buffer to hold the identify data
* **nsid (int)**\ : nsid field in the command. Default: 0
* **cns (int)**\ : cns field in the command. Default: 1
* **cb (function)**\ : callback function called at completion. Default: None

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

**Parameters**


* **func (function)**\ : callback function called at aer completion

reset
^^^^^

.. code-block:: python

   Controller.reset(self)

controller reset: cc.en 1 => 0 => 1

Notice
    Test scripts should delete all io qpairs before reset!

sanitize
^^^^^^^^

.. code-block:: python

   Controller.sanitize(self, option, pattern, cb)

sanitize admin command

**Parameters**


* **option (int)**\ : sanitize option field in the command
* **pattern (int)**\ : pattern field in the command for overwrite method. Default: 0x5aa5a55a
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


send_cmd
^^^^^^^^

.. code-block:: python

   Controller.send_cmd(self, opcode, buf, nsid, cdw10, cdw11, cdw12, cdw13, cdw14, cdw15, cb)

send generic admin commands.

This is a generic method. Scripts can use this method to send all kinds of commands, like Vendor Specific commands, and even not existed commands.

**Parameters**


* **opcode (int)**\ : operate code of the command
* **buf (Buffer)**\ : buffer of the command. Default: None
* **nsid (int)**\ : nsid field of the command. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


setfeatures
^^^^^^^^^^^

.. code-block:: python

   Controller.setfeatures(self, fid, cdw11, cdw12, cdw13, cdw14, cdw15, sv, buf, cb)

setfeatures admin command

**Parameters**


* **fid (int)**\ : feature id
* **cdw11 (int)**\ : cdw11 in the command. Default: 0
* **sv (int)**\ : sv field in the command. Default: 0
* **buf (Buffer)**\ : the buffer to hold the feature data. Default: None
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

.. code-block::

   self (Controller)


supports
^^^^^^^^

.. code-block:: python

   Controller.supports(self, opcode)

check if the admin command is supported

**Parameters**


* **opcode (int)**\ : the opcode of the admin command

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

Notice
    Do not call this function in commands callback functions.

**Parameters**


* **expected (int)**\ : expected commands to complete. Default: 1

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

**Parameters**


* **nvme (Controller)**\ : controller where to create the queue
* **nsid (int)**\ : nsid of the namespace

capacity
^^^^^^^^

bytes of namespace capacity

close
^^^^^

.. code-block:: python

   Namespace.close(self)

close namespace to release it resources in host memory.

Notice
    Release resources explictly, del is not garentee to call **dealloc**.
    Fixture nvme0n1 uses this function, and prefer to use fixture in scripts, instead of calling this function directly.

cmdname
^^^^^^^

.. code-block:: python

   Namespace.cmdname(self, opcode)

get the name of the IO command

**Parameters**


* **opcode (int)**\ : the opcode of the IO command

**Returns**

``(str)``\ : the command name

compare
^^^^^^^

.. code-block:: python

   Namespace.compare(self, qpair, buf, lba, lba_count, io_flags, cb)

compare IO command

Notice
    buf cannot be released before the command completes.

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **buf (Buffer)**\ : the data buffer of the command, meta data is not supported.
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits. Default: 1
* **io_flags (int)**\ : io flags defined in NVMe specification, 16 bits. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

dsm
^^^

.. code-block:: python

   Namespace.dsm(self, qpair, buf, range_count, attribute, cb)

data-set management IO command

Notice
    buf cannot be released before the command completes.

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **buf (Buffer)**\ : the buffer of the lba ranges. Use buffer.set_dsm_range to prepare the buffer.
* **range_count (int)**\ : the count of lba ranges in the buffer
* **attribute (int)**\ : attribute field of the command. Default: 0x4, as deallocation/trim
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

flush
^^^^^

.. code-block:: python

   Namespace.flush(self, qpair, cb)

flush IO command

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

format
^^^^^^

.. code-block:: python

   Namespace.format(self, data_size, meta_size, ses)

change the format of this namespace

Notice
    this facility not only sends format admin command, but also updates driver to activate new format immediately

**Parameters**


* **data_size (int)**\ : data size. Default: 512
* **meta_size (int)**\ : meta data size. Default: 0
* **ses (int)**\ : ses field in the command. Default: 0, no secure erase

**Returns**

``(int or None)``\ : the lba format has the specified data size and meta data size

get_lba_format
^^^^^^^^^^^^^^

.. code-block:: python

   Namespace.get_lba_format(self, data_size, meta_size)

find the lba format by its data size and meta data size

**Parameters**


* **data_size (int)**\ : data size. Default: 512
* **meta_size (int)**\ : meta data size. Default: 0

**Returns**

``(int or None)``\ : the lba format has the specified data size and meta data size

id_data
^^^^^^^

.. code-block:: python

   Namespace.id_data(self, byte_end, byte_begin, type)

get field in namespace identify data

**Parameters**


* **byte_end (int)**\ : the end byte number of this field, which is specified in NVMe spec. Included.
* **byte_begin (int)**\ : the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* **type (type)**\ : the type of the field. It should be int or str. Default: int, convert to integer python object

**Returns**

``(int or str)``\ : the data in the specified field

ioworker
^^^^^^^^

.. code-block:: python

   Namespace.ioworker(self, io_size, lba_step, lba_align, lba_random, read_percentage, time, qdepth, region_start, region_end, iops, io_count, lba_start, qprio, distribution, pvalue, ptype, output_io_per_second, output_percentile_latency, output_cmdlog_list)

workers sending different read/write IO on different CPU cores.

User defines IO characteristics in parameters, and then the ioworker
executes without user intervesion, until the test is completed. IOWorker
returns some statistic data at last.

User can start multiple IOWorkers, and they will be binded to different
CPU cores. Each IOWorker creates its own Qpair, so active IOWorker counts
is limited by maximum IO queues that DUT can provide.

Each ioworker can run upto 24 hours.

**Parameters**


* **io_size (short, range, list, dict)**\ : IO size, unit is LBA. It can be a fixed size, or a range or list of size, or specify ratio in the dict if they are not evenly distributed
* **lba_step (short)**\ : valid only for sequential read/write, jump to next LBA by the step. Default: None, same as io_size, continous IO.
* **lba_align (short)**\ : IO alignment, unit is LBA. Default: None: same as io_size when it < 4K, or it is 4K
* **lba_random (bool)**\ : True if sending IO with random starting LBA. Default: True
* **read_percentage (int)**\ : sending read/write mixed IO, 0 means write only, 100 means read only. Default: 100
* **time (int)**\ : specified maximum time of the IOWorker in seconds, up to 1000*3600. Default:0, means no limit
* **qdepth (int)**\ : queue depth of the Qpair created by the IOWorker, up to 1024. Default: 64
* **region_start (long)**\ : sending IO in the specified LBA region, start. Default: 0
* **region_end (long)**\ : sending IO in the specified LBA region, end but not include. Default: 0xffff_ffff_ffff_ffff
* **iops (int)**\ : specified maximum IOPS. IOWorker throttles the sending IO speed. Default: 0, means no limit
* **io_count (long)**\ : specified maximum IO counts to send. Default: 0, means no limit
* **lba_start (long)**\ : the LBA address of the first command. Default: 0, means start from region_start
* **qprio (int)**\ : SQ priority. Default: 0, as Round Robin arbitration
* **distribution (list(int))**\ : distribute 10,000 IO to 100 sections. Default: None
* **pvalue (int)**\ : data pattern value. Refer to data pattern in class ``Buffer``. Default: 0
* **ptype (int)**\ : data pattern type. Refer to data pattern in class ``Buffer``. Default: 0
* **output_io_per_second (list)**\ : list to hold the output data of io_per_second. Default: None, not to collect the data
* **output_percentile_latency (dict)**\ : dict of io counter on different percentile latency. Dict key is the percentage, and the value is the latency in micro-second. Default: None, not to collect the data
* **output_cmdlog_list (list)**\ : list of dwords of lastest commands sent in the ioworker. Default: None, not to collect the data

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

Notice
    buf cannot be released before the command completes.

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **buf (Buffer)**\ : the data buffer of the command, meta data is not supported.
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits. Default: 1
* **io_flags (int)**\ : io flags defined in NVMe specification, 16 bits. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the read command fails

send_cmd
^^^^^^^^

.. code-block:: python

   Namespace.send_cmd(self, opcode, qpair, buf, nsid, cdw10, cdw11, cdw12, cdw13, cdw14, cdw15, cb)

send generic IO commands.

This is a generic method. Scripts can use this method to send all kinds of commands, like Vendor Specific commands, and even not existed commands.

**Parameters**


* **opcode (int)**\ : operate code of the command
* **qpair (Qpair)**\ : qpair used to send this command
* **buf (Buffer)**\ : buffer of the command. Default: None
* **nsid (int)**\ : nsid field of the command. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

supports
^^^^^^^^

.. code-block:: python

   Namespace.supports(self, opcode)

check if the IO command is supported

**Parameters**


* **opcode (int)**\ : the opcode of the IO command

**Returns**

``(bool)``\ : if the command is supported

write
^^^^^

.. code-block:: python

   Namespace.write(self, qpair, buf, lba, lba_count, io_flags, cb)

write IO command

Notice
    buf cannot be released before the command completes.

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **buf (Buffer)**\ : the data buffer of the write command, meta data is not supported.
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits
* **io_flags (int)**\ : io flags defined in NVMe specification, 16 bits. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the write command fails

write_uncorrectable
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   Namespace.write_uncorrectable(self, qpair, lba, lba_count, cb)

write uncorrectable IO command

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits. Default: 1
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

write_zeroes
^^^^^^^^^^^^

.. code-block:: python

   Namespace.write_zeroes(self, qpair, lba, lba_count, io_flags, cb)

write zeroes IO command

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits. Default: 1
* **io_flags (int)**\ : io flags defined in NVMe specification, 16 bits. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

**Returns**

``qpair (Qpair)``\ : the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

Pcie
----

.. code-block:: python

   Pcie(self, /, *args, **kwargs)

Pcie class. Prefer to use fixture "pcie" in test scripts

**Parameters**


* **nvme (Controller)**\ : the nvme controller object of that subsystem

aspm
^^^^

current ASPM setting

cap_offset
^^^^^^^^^^

.. code-block:: python

   Pcie.cap_offset(self, cap_id)

get the offset of a capability

**Parameters**


* **cap_id (int)**\ : capability id

**Returns**

``(int)``\ : the offset of the register, or None if the capability is not existed

power_state
^^^^^^^^^^^

current power state

register
^^^^^^^^

.. code-block:: python

   Pcie.register(self, offset, byte_count)

access registers in pcie config space, and get its integer value.

**Parameters**


* **offset (int)**\ : the offset (in bytes) of the register in the config space
* **byte_count (int)**\ : the size (in bytes) of the register

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

**Parameters**


* **nvme (Controller)**\ : controller where to create the queue
* **depth (int)**\ : SQ/CQ queue depth
* **prio (int)**\ : when Weighted Round Robin is enabled, specify SQ priority here

cmdlog
^^^^^^

.. code-block:: python

   Qpair.cmdlog(self, count)

print recent IO commands and their completions in this qpair.

**Parameters**


* **count (int)**\ : the number of commands to print. Default: 0, to print the whole cmdlog

waitdone
^^^^^^^^

.. code-block:: python

   Qpair.waitdone(self, expected)

sync until expected commands completion

Notice
    Do not call this function in commands callback functions.

**Parameters**


* **expected (int)**\ : expected commands to complete. Default: 1

srand
-----

.. code-block:: python

   srand(seed)

setup random seed

**Parameters**


* **seed (int)**\ : the seed to setup for both python and C library

Subsystem
---------

.. code-block:: python

   Subsystem(self, /, *args, **kwargs)

Subsystem class. Prefer to use fixture "subsystem" in test scripts.

**Parameters**


* **nvme (Controller)**\ : the nvme controller object of that subsystem

power_cycle
^^^^^^^^^^^

.. code-block:: python

   Subsystem.power_cycle(self, sec)

power off and on in seconds

**Parameters**


* **sec (int)**\ : the seconds between power off and power on

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

**Parameters**


* **abrupt (bool)**\ : it will be an abrupt shutdown (return immediately) or clean shutdown (wait shutdown completely)
