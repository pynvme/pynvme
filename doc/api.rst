
nvme
====

Buffer
------

.. code-block:: python

   Buffer()

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

   Buffer.data(byte_end, byte_begin, type)

get field in the buffer. Little endian for integers.

**Parameters**


* **byte_end (int)**\ : the end byte number of this field, which is specified in NVMe spec. Included.
* **byte_begin (int)**\ : the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* **type (type)**\ : the type of the field. It should be int or str. Default: int, convert to integer python object

Returns
    (int or str): the data in the specified field

dump
^^^^

.. code-block:: python

   Buffer.dump(size)

get the buffer content

**Parameters**


* **size (int)**\ : the size of the buffer to print. Default: None, means to print the whole buffer

phys_addr
^^^^^^^^^

physical address of the buffer

set_dsm_range
^^^^^^^^^^^^^

.. code-block:: python

   Buffer.set_dsm_range(index, lba, lba_count, attr)

set dsm ranges in the buffer, for dsm/deallocation (a.k.a. trim) commands

**Parameters**


* **index (int)**\ : the index of the dsm range to set
* **lba (int)**\ : the start lba of the range
* **lba_count (int)**\ : the lba count of the range
* **attr (int)**\ : context attributes of the range

Controller
----------

.. code-block:: python

   Controller()

Controller class. Prefer to use fixture "nvme0" in test scripts.

**Parameters**


* **pcie (Pcie)**\ : Pcie object, or Tcp object for NVMe TCP targets
* **nvme_init_func (callable, bool, None)**\ : True: no nvme init process, None: default process, callable: user defined process function

**Example**

.. code-block:: shell

       >>> n = Controller(Pcie('01:00.0'))
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

   Controller.abort(cid, sqid, cb)

abort admin commands

**Parameters**


* **cid (int)**\ : command id of the command to be aborted
* **sqid (int)**\ : sq id of the command to be aborted. Default: 0, to abort the admin command
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

aer
^^^

.. code-block:: python

   Controller.aer(cb)

asynchorous event request admin command.

Not suggested to use this command in scripts because driver manages to send and monitor aer commands. Scripts should register an aer callback function if it wants to handle aer, and use the fixture aer.

**Parameters**


* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

cap
^^^

64-bit CAP register of NVMe

cmdlog
^^^^^^

.. code-block:: python

   Controller.cmdlog(count)

print recent commands and their completions.

**Parameters**


* **count (int)**\ : the number of commands to print. Default: 0, to print the whole cmdlog

cmdname
^^^^^^^

.. code-block:: python

   Controller.cmdname(opcode)

get the name of the admin command

**Parameters**


* **opcode (int)**\ : the opcode of the admin command

Returns
    (str): the command name

downfw
^^^^^^

.. code-block:: python

   Controller.downfw(filename, slot, action)

firmware download utility: by 4K, and activate in next reset

**Parameters**


* **filename (str)**\ : the pathname of the firmware binary file to download
* **slot (int)**\ : firmware slot field in the command. Default: 0, decided by device
* **cb (function)**\ : callback function called at completion. Default: None

Returns

dst
^^^

.. code-block:: python

   Controller.dst(stc, nsid, cb)

device self test (DST) admin command

**Parameters**


* **stc (int)**\ : selftest code (stc) field in the command
* **nsid (int)**\ : nsid field in the command. Default: 0xffffffff
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

format
^^^^^^

.. code-block:: python

   Controller.format(lbaf, ses, nsid, cb)

format admin command

Notice
    This Controller.format only send the admin command. Use Namespace.format to maintain pynvme internal data!

**Parameters**


* **lbaf (int)**\ : lbaf (lba format) field in the command. Default: 0
* **ses (int)**\ : ses field in the command. Default: 0, no secure erase
* **nsid (int)**\ : nsid field in the command. Default: 1
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

fw_commit
^^^^^^^^^

.. code-block:: python

   Controller.fw_commit(slot, action, cb)

firmware commit admin command

**Parameters**


* **slot (int)**\ : firmware slot field in the command
* **action (int)**\ : action field in the command
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

fw_download
^^^^^^^^^^^

.. code-block:: python

   Controller.fw_download(buf, offset, size, cb)

firmware download admin command

**Parameters**


* **buf (Buffer)**\ : the buffer to hold the firmware data
* **offset (int)**\ : offset field in the command
* **size (int)**\ : size field in the command. Default: None, means the size of the buffer
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

getfeatures
^^^^^^^^^^^

.. code-block:: python

   Controller.getfeatures(fid, sel, buf, cdw11, cdw12, cdw13, cdw14, cdw15,
                          cb)

getfeatures admin command

**Parameters**


* **fid (int)**\ : feature id
* **cdw11 (int)**\ : cdw11 in the command. Default: 0
* **sel (int)**\ : sel field in the command. Default: 0
* **buf (Buffer)**\ : the buffer to hold the feature data. Default: None
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

getlogpage
^^^^^^^^^^

.. code-block:: python

   Controller.getlogpage(lid, buf, size, offset, nsid, cb)

getlogpage admin command

**Parameters**


* **lid (int)**\ : Log Page Identifier
* **buf (Buffer)**\ : buffer to hold the log page
* **size (int)**\ : size (in byte) of data to get from the log page,. Default: None, means the size is the same of the buffer
* **offset (int)**\ : the location within a log page
* **nsid (int)**\ : nsid field in the command. Default: 0xffffffff
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

id_data
^^^^^^^

.. code-block:: python

   Controller.id_data(byte_end, byte_begin, type, nsid, cns)

get field in controller identify data

**Parameters**


* **byte_end (int)**\ : the end byte number of this field, which is specified in NVMe spec. Included.
* **byte_begin (int)**\ : the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* **type (type)**\ : the type of the field. It should be int or str. Default: int, convert to integer python object

Returns
    (int or str): the data in the specified field

identify
^^^^^^^^

.. code-block:: python

   Controller.identify(buf, nsid, cns, cntid, csi, nvmsetid, cb)

identify admin command

**Parameters**


* **buf (Buffer)**\ : the buffer to hold the identify data
* **nsid (int)**\ : nsid field in the command. Default: 0
* **cns (int)**\ : cns field in the command. Default: 1
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

init_adminq
^^^^^^^^^^^

.. code-block:: python

   Controller.init_adminq()

used by NVMe init process in scripts

init_ns
^^^^^^^

.. code-block:: python

   Controller.init_ns()

used by NVMe init process in scripts

init_queues
^^^^^^^^^^^

.. code-block:: python

   Controller.init_queues(cdw0)

used by NVMe init process in scripts

latest_cid
^^^^^^^^^^

cid of latest completed command

latest_latency
^^^^^^^^^^^^^^

latency of latest completed command in us

mdts
^^^^

max data transfer bytes

mi_receive
^^^^^^^^^^

.. code-block:: python

   Controller.mi_receive(opcode, dword0, dword1, buf, mtype, cb)

NVMe MI receive

**Parameters**


* **opcode (int)**\ : MI opcode
* **dword0 (int)**\ : MI request dword0
* **dword1 (int)**\ : MI request dword1
* **buf (Buffer)**\ : buffer to hold the response data
* **mtype (int)**\ : MI message type. Default:1, MI command set
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

mi_send
^^^^^^^

.. code-block:: python

   Controller.mi_send(opcode, dword0, dword1, buf, mtype, cb)

NVMe MI Send

**Parameters**


* **opcode (int)**\ : MI opcode
* **dword0 (int)**\ : MI request dword0
* **dword1 (int)**\ : MI request dword1
* **buf (Buffer)**\ : buffer to hold the request data
* **mtype (int)**\ : MI message type. Default:1, MI command set
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

reset
^^^^^

.. code-block:: python

   Controller.reset()

controller reset: cc.en 1 => 0 => 1

Notice
    Test scripts should delete all io qpairs before reset!

sanitize
^^^^^^^^

.. code-block:: python

   Controller.sanitize(option, pattern, cb)

sanitize admin command

**Parameters**


* **option (int)**\ : sanitize option field in the command
* **pattern (int)**\ : pattern field in the command for overwrite method. Default: 0x5aa5a55a
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

security_receive
^^^^^^^^^^^^^^^^

.. code-block:: python

   Controller.security_receive(buf, spsp, secp, nssf, size, cb)

admin command: security receive

**Parameters**


* **buf (Buffer)**\ : buffer of the data received
* **spsp**\ : SP specific 0/1, 16bit filed
* **secp**\ : security protocal, default 1, TCG
* **nssf**\ : NVMe security specific field: default 0, reserved
* **size**\ : size of the data to receive, default the same size of the buffer
* **cb (function)**\ : callback function called at cmd completion

security_send
^^^^^^^^^^^^^

.. code-block:: python

   Controller.security_send(buf, spsp, secp, nssf, size, cb)

admin command: security send

**Parameters**


* **buf (Buffer)**\ : buffer of the data sending
* **spsp**\ : SP specific 0/1, 16bit filed
* **secp**\ : security protocal, default 1, TCG
* **nssf**\ : NVMe security specific field: default 0, reserved
* **size**\ : size of the data to send, default the same size of the buffer
* **cb (function)**\ : callback function called at cmd completion

send_cmd
^^^^^^^^

.. code-block:: python

   Controller.send_cmd(opcode, buf, nsid, cdw10, cdw11, cdw12, cdw13, cdw14,
                       cdw15, cb)

send generic admin commands.

This is a generic method. Scripts can use this method to send all kinds of commands, like Vendor Specific commands, and even not existed commands.

**Parameters**


* **opcode (int)**\ : operate code of the command
* **buf (Buffer)**\ : buffer of the command. Default: None
* **nsid (int)**\ : nsid field of the command. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

setfeatures
^^^^^^^^^^^

.. code-block:: python

   Controller.setfeatures(fid, sv, buf, cdw11, cdw12, cdw13, cdw14, cdw15,
                          cb)

setfeatures admin command

**Parameters**


* **fid (int)**\ : feature id
* **cdw11 (int)**\ : cdw11 in the command. Default: 0
* **sv (int)**\ : sv field in the command. Default: 0
* **buf (Buffer)**\ : the buffer to hold the feature data. Default: None
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    self (Controller)

supports
^^^^^^^^

.. code-block:: python

   Controller.supports(opcode)

check if the admin command is supported

**Parameters**


* **opcode (int)**\ : the opcode of the admin command

Returns
    (bool): if the command is supported

timeout
^^^^^^^

timeout value of this controller in milli-seconds.

It is configurable by assigning new value in milli-seconds.

waitdone
^^^^^^^^

.. code-block:: python

   Controller.waitdone(expected)

sync until expected admin commands completion

Notice
    Do not call this function in commands callback functions.

**Parameters**


* **expected (int)**\ : expected commands to complete. Default: 1

Returns
    (int): cdw0 of the last command

Namespace
---------

.. code-block:: python

   Namespace()

Namespace class.

**Parameters**


* **nvme (Controller)**\ : controller where to create the queue
* **nsid (int)**\ : nsid of the namespace. Default 1
* **nlba_verify (long)**\ : number of LBAs where data verificatoin is enabled. Default 0, the whole namespace

capacity
^^^^^^^^

bytes of namespace capacity

close
^^^^^

.. code-block:: python

   Namespace.close()

close to explictly release its resources instead of del

cmdname
^^^^^^^

.. code-block:: python

   Namespace.cmdname(opcode)

get the name of the IO command

**Parameters**


* **opcode (int)**\ : the opcode of the IO command

Returns
    (str): the command name

compare
^^^^^^^

.. code-block:: python

   Namespace.compare(qpair, buf, lba, lba_count, io_flags, cb)

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

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

dsm
^^^

.. code-block:: python

   Namespace.dsm(qpair, buf, range_count, attribute, cb)

data-set management IO command

Notice
    buf cannot be released before the command completes.

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **buf (Buffer)**\ : the buffer of the lba ranges. Use buffer.set_dsm_range to prepare the buffer.
* **range_count (int)**\ : the count of lba ranges in the buffer
* **attribute (int)**\ : attribute field of the command. Default: 0x4, as deallocation/trim
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

flush
^^^^^

.. code-block:: python

   Namespace.flush(qpair, cb)

flush IO command

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

format
^^^^^^

.. code-block:: python

   Namespace.format(data_size, meta_size, ses)

change the format of this namespace

Notice
    Namespace.format() not only sends the admin command, but also updates driver to activate new format immediately. Recommend to use this API to do format. Close and re-create namespace when lba format is changed.

**Parameters**


* **data_size (int)**\ : data size. Default: 512
* **meta_size (int)**\ : meta data size. Default: 0
* **ses (int)**\ : ses field in the command. Default: 0, no secure erase

Returns
    int: cdw0 of the format admin command

get_lba_format
^^^^^^^^^^^^^^

.. code-block:: python

   Namespace.get_lba_format(data_size, meta_size)

find the lba format by its data size and meta data size

**Parameters**


* **data_size (int)**\ : data size. Default: 512
* **meta_size (int)**\ : meta data size. Default: 0

Returns
    (int or None): the lba format has the specified data size and meta data size

id_data
^^^^^^^

.. code-block:: python

   Namespace.id_data(byte_end, byte_begin, type)

get field in namespace identify data

**Parameters**


* **byte_end (int)**\ : the end byte number of this field, which is specified in NVMe spec. Included.
* **byte_begin (int)**\ : the begin byte number of this field, which is specified in NVMe spec. It can be omitted if begin is the same as end when the field has only 1 byte. Included. Default: None, means only get 1 byte defined in byte_end
* **type (type)**\ : the type of the field. It should be int or str. Default: int, convert to integer python object

Returns
    (int or str): the data in the specified field

ioworker
^^^^^^^^

.. code-block:: python

   Namespace.ioworker(io_size, lba_step, lba_align, lba_random,
                      read_percentage, op_percentage, time, qdepth,
                      region_start, region_end, iops, io_count, lba_start,
                      qprio, distribution, ptype, pvalue, io_sequence,
                      fw_debug, output_io_per_second,
                      output_percentile_latency, output_cmdlog_list)

workers sending different read/write IO on different CPU cores.

User defines IO characteristics in parameters, and then the ioworker
executes without user intervesion, until the test is completed. IOWorker
returns some statistic data at last.

User can start multiple IOWorkers, and they will be binded to different
CPU cores. Each IOWorker creates its own Qpair, so active IOWorker counts
is limited by maximum IO queues that DUT can provide.

Each ioworker can run upto 24 hours.

**Parameters**


* **io_size (short, range, list, dict)**\ : IO size, unit is LBA. It can be a fixed size, or a range or list of size, or specify ratio in the dict if they are not evenly distributed. 1base. Default: 8, 4K
* **lba_step (short)**\ : valid only for sequential read/write, jump to next LBA by the step. Default: None, same as io_size, continous IO.
* **lba_align (short)**\ : IO alignment, unit is LBA. Default: None: means 1 lba.
* **lba_random (int, bool)**\ : percentage of radom io, or True if sending IO with all random starting LBA. Default: True
* **read_percentage (int)**\ : sending read/write mixed IO, 0 means write only, 100 means read only. Default: 100. Obsoloted by op_percentage
* **op_percentage (dict)**\ : opcode of commands sent in ioworker, and their percentage. Output: real io counts sent in ioworker. Default: None, fall back to read_percentage
* **time (int)**\ : specified maximum time of the IOWorker in seconds, up to 1000*3600. Default:0, means no limit
* **qdepth (int)**\ : queue depth of the Qpair created by the IOWorker, up to 1024. 1base value. Default: 64
* **region_start (long)**\ : sending IO in the specified LBA region, start. Default: 0
* **region_end (long)**\ : sending IO in the specified LBA region, end but not include. Default: 0xffff_ffff_ffff_ffff
* **iops (int)**\ : specified maximum IOPS. IOWorker throttles the sending IO speed. Default: 0, means no limit
* **io_count (long)**\ : specified maximum IO counts to send. Default: 0, means no limit
* **lba_start (long)**\ : the LBA address of the first command. Default: 0, means start from region_start
* **qprio (int)**\ : SQ priority. Default: 0, as Round Robin arbitration
* **distribution (list(int))**\ : distribute 10,000 IO to 100 sections. Default: None
* **pvalue (int)**\ : data pattern value. Refer to data pattern in class ``Buffer``. Default: 100 (100%)
* **ptype (int)**\ : data pattern type. Refer to data pattern in class ``Buffer``. Default: 0xbeef (random data)
* **io_sequence (list)**\ : io sequence of captured trace from real workload. Ignore other input parameters when io_sequence is given. Default: None
* **output_io_per_second (list)**\ : list to hold the output data of io_per_second. Default: None, not to collect the data
* **output_percentile_latency (dict)**\ : dict of io counter on different percentile latency. Dict key is the percentage, and the value is the latency in micro-second. Default: None, not to collect the data
* **output_cmdlog_list (list)**\ : list of dwords of lastest commands completed in the ioworker. Default: None, not to collect the data

Returns
    ioworker instance

nsid
^^^^

id of the namespace

read
^^^^

.. code-block:: python

   Namespace.read(qpair, buf, lba, lba_count, io_flags, dword13, dword14,
                  dword15, cb)

read IO command

Notice
    buf cannot be released before the command completes.

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **buf (Buffer)**\ : the data buffer of the command, meta data is not supported.
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits. Default: 1
* **io_flags (int)**\ : io flags defined in NVMe specification, 16 bits. Default: 0
* **dword13 (int)**\ : command SQE dword13
* **dword14 (int)**\ : command SQE dword14
* **dword15 (int)**\ : command SQE dword15
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

send_cmd
^^^^^^^^

.. code-block:: python

   Namespace.send_cmd(opcode, qpair, buf, nsid, cdw10, cdw11, cdw12, cdw13,
                      cdw14, cdw15, cb)

send generic IO commands.

This is a generic method. Scripts can use this method to send all kinds of commands, like Vendor Specific commands, and even not existed commands.

**Parameters**


* **opcode (int)**\ : operate code of the command
* **qpair (Qpair)**\ : qpair used to send this command
* **buf (Buffer)**\ : buffer of the command. Default: None
* **nsid (int)**\ : nsid field of the command. Default: 0
* **cdw1x (int)**\ : command SQE dword10 - dword15
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

supports
^^^^^^^^

.. code-block:: python

   Namespace.supports(opcode)

check if the IO command is supported

**Parameters**


* **opcode (int)**\ : the opcode of the IO command

Returns
    (bool): if the command is supported

verify
^^^^^^

.. code-block:: python

   Namespace.verify(qpair, lba, lba_count, io_flags, cb)

verify IO command

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits. Default: 1
* **io_flags (int)**\ : io flags defined in NVMe specification, 16 bits. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the read command fails

verify_enable
^^^^^^^^^^^^^

.. code-block:: python

   Namespace.verify_enable(enable)

enable or disable the inline verify function of the namespace

**Parameters**


* **enable (bool)**\ : enable or disable the verify function

Returns
    (bool): if it is enabled successfully

write
^^^^^

.. code-block:: python

   Namespace.write(qpair, buf, lba, lba_count, io_flags, dword13, dword14,
                   dword15, cb)

write IO command

Notice
    buf cannot be released before the command completes.

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **buf (Buffer)**\ : the data buffer of the write command, meta data is not supported.
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits
* **io_flags (int)**\ : io flags defined in NVMe specification, 16 bits. Default: 0
* **dword13 (int)**\ : command SQE dword13
* **dword14 (int)**\ : command SQE dword14
* **dword15 (int)**\ : command SQE dword15
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

write_uncorrectable
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   Namespace.write_uncorrectable(qpair, lba, lba_count, cb)

write uncorrectable IO command

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits. Default: 1
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

write_zeroes
^^^^^^^^^^^^

.. code-block:: python

   Namespace.write_zeroes(qpair, lba, lba_count, io_flags, cb)

write zeroes IO command

**Parameters**


* **qpair (Qpair)**\ : use the qpair to send this command
* **lba (int)**\ : the starting lba address, 64 bits
* **lba_count (int)**\ : the lba count of this command, 16 bits. Default: 1
* **io_flags (int)**\ : io flags defined in NVMe specification, 16 bits. Default: 0
* **cb (function)**\ : callback function called at completion. Default: None

Returns
    qpair (Qpair): the qpair used to send this command, for ease of chained call

**Raises**


* ``SystemError``\ : the command fails

Pcie
----

.. code-block:: python

   Pcie()

Pcie class to access PCIe configuration and memory space

**Parameters**


* **addr (str)**\ : BDF address of PCIe device

aspm
^^^^

config new ASPM Control:

**Parameters**


* **control**\ : ASPM control field in Link Control register:
* **b00**\ : ASPM is disabled
* **b01**\ : L0s
* **b10**\ : L1
* **b11**\ : L0s and L1

cap_offset
^^^^^^^^^^

.. code-block:: python

   Pcie.cap_offset(cap_id)

get the offset of a capability

**Parameters**


* **cap_id (int)**\ : capability id

Returns
    (int): the offset of the register, or None if the capability is not existed

close
^^^^^

.. code-block:: python

   Pcie.close()

close to explictly release its resources instead of del

power_state
^^^^^^^^^^^

config new power state:

**Parameters**


* **state**\ : new state of the PCIe device:
* **0**\ : D0
* **1**\ : D1
* **2**\ : D2
* **3**\ : D3hot

register
^^^^^^^^

.. code-block:: python

   Pcie.register(offset, byte_count)

access registers in pcie config space, and get its integer value.

**Parameters**


* **offset (int)**\ : the offset (in bytes) of the register in the config space
* **byte_count (int)**\ : the size (in bytes) of the register. Default: 4, dword

Returns
    (int): the value of the register

reset
^^^^^

.. code-block:: python

   Pcie.reset(rst_fn)

reset this pcie device with hot reset

Notice
    call Controller.reset() to re-initialize controller after this reset

Qpair
-----

.. code-block:: python

   Qpair()

Qpair class. IO SQ and CQ are combinded as qpairs.

**Parameters**


* **nvme (Controller)**\ : controller where to create the queue
* **depth (int)**\ : SQ/CQ queue depth
* **prio (int)**\ : when Weighted Round Robin is enabled, specify SQ priority here

cmdlog
^^^^^^

.. code-block:: python

   Qpair.cmdlog(count)

print recent IO commands and their completions in this qpair.

**Parameters**


* **count (int)**\ : the number of commands to print. Default: 0, to print the whole cmdlog

delete
^^^^^^

.. code-block:: python

   Qpair.delete()

delete qpair's SQ and CQ

latest_cid
^^^^^^^^^^

cid of latest completed command

latest_latency
^^^^^^^^^^^^^^

latency of latest completed command in us

sqid
^^^^

submission queue id in this qpair

waitdone
^^^^^^^^

.. code-block:: python

   Qpair.waitdone(expected)

sync until expected IO commands completion

Notice
    Do not call this function in commands callback functions.

**Parameters**


* **expected (int)**\ : expected commands to complete. Default: 1

Returns
    (int): cdw0 of the last command

srand
-----

.. code-block:: python

   srand(seed)

manually setup random seed

**Parameters**


* **seed (int)**\ : the seed to setup for both python and C library

Subsystem
---------

.. code-block:: python

   Subsystem()

Subsystem class. Prefer to use fixture "subsystem" in test scripts.

**Parameters**


* **nvme (Controller)**\ : the nvme controller object of that subsystem
* **poweron_cb (func)**\ : callback of poweron function
* **poweroff_cb (func)**\ : callback of poweroff function

power_cycle
^^^^^^^^^^^

.. code-block:: python

   Subsystem.power_cycle(sec)

power off and on in seconds

Notice
    call Controller.reset() to re-initialize controller after this power cycle

**Parameters**


* **sec (int)**\ : the seconds between power off and power on

poweroff
^^^^^^^^

.. code-block:: python

   Subsystem.poweroff()

power off the device by the poweroff function provided in Subsystem initialization

poweron
^^^^^^^

.. code-block:: python

   Subsystem.poweron()

power on the device by the poweron function provided in Subsystem initialization

Notice
    call Controller.reset() to re-initialize controller after this power on

reset
^^^^^

.. code-block:: python

   Subsystem.reset()

reset the nvme subsystem through register nssr.nssrc

Notice
    call Controller.reset() to re-initialize controller after this reset

shutdown_notify
^^^^^^^^^^^^^^^

.. code-block:: python

   Subsystem.shutdown_notify(abrupt)

notify nvme subsystem a shutdown event through register cc.shn

**Parameters**


* **abrupt (bool)**\ : it will be an abrupt shutdown (return immediately) or clean shutdown (wait shutdown completely)

Tcp
---

.. code-block:: python

   Tcp()

Tcp class for NVMe TCP target

**Parameters**


* **addr (str)**\ : IP address of TCP target
* **port (int)**\ : the port number of TCP target. Default: 4420
