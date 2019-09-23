Features
========

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
#. timeout
#. data pattern

by classes, methods


Pynvme writes and reads data in buffer to NVMe device LBA space. In order to verify the data integrity, it injects LBA address and version information into the write data buffer, and check with them after read completion. Furthermore, Pynvme computes and verifies CRC32 of each LBA on the fly. Both data buffer and LBA CRC32 are stored in host memory, so ECC memory are recommended if you are considering serious tests.

Buffer should be allocated for data commands, and held till that command is completed because the buffer is being used by NVMe device. Users need to pay more attention on the life scope of the buffer in Python test scripts.

NVMe commands are all asynchronous. Test scripts can sync through waitdone() method to make sure the command is completed. The method waitdone() polls command Completion Queues. When the optional callback function is provided in a command in python scripts, the callback function is called when that command is completed in waitdone(). The command timeout is configurable, and the default time is 10 seconds.

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



After installation, pynvme generates the binary extension which can be import-ed in python scripts. Example:

.. code-block:: python

   import nvme as d

   nvme0 = d.Controller(b"01:00.0")  # initialize NVMe controller with its PCIe BDF address
   id_buf = d.Buffer(4096)  # allocate the buffer
   nvme0.identify(id_buf, nsid=0xffffffff, cns=1)  # read namespace identify data into buffer
   nvme0.waitdone()  # nvme commands are executed asynchronously, so we have to wait the completion before access the id_buf.
   print(id_buf.dump())   # print the whole buffer

In order to write test scripts more efficently, pynvme provides pytest fixtures. We can write more in intuitive test scripts. Example:

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
