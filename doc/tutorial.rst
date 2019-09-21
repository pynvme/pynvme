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
