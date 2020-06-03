Examples
========

In this chapter, we will review several typical NVMe test scripts. 

Ex1: hello world
----------------

.. code-block:: python

   # import packages
   import pytest
   import nvme as d

   # define the test case in a python function
   # list fixtures used in the parameter list
   # specify the class type of the fixture, so VSCode can give more docstring online
   def test_hello_world(nvme0, nvme0n1: d.Namespace):
       # create the buffers and fill data for read/write commands
       read_buf = d.Buffer(512)
       data_buf = d.Buffer(512)
       data_buf[10:21] = b'hello world'

       # create IO Qpair for read/write commands
       qpair = d.Qpair(nvme0, 16) 

       # Define the callback function for write command. 
       # The argument *status1* of the callback is a 16-bit
       # value, which includes the Phase-bit.
       def write_cb(cdw0, status1):
           nvme0n1.read(qpair, read_buf, 0, 1)

       # execute the write command with the callback function
       nvme0n1.write(qpair, data_buf, 0, 1, cb=write_cb)

       # wait the write command, and the read command in its callback, to be completed
       qpair.waitdone(2)

       # check the data in read buffer
       assert read_buf[10:21] == b'hello world'


Ex2: sanitize
-------------

.. code-block:: python

   # import more package for GUI programming
   import PySimpleGUI as sg

   # define another test function, use the default buffer created by the fixture
   def test_sanitize(nvme0, nvme0n1, buf):
       # check if sanitize is supported by the device
       if nvme0.id_data(331, 328) == 0:
           pytest.skip("sanitize operation is not supported")

       # start sanitize operation
       logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))
       nvme0.sanitize().waitdone()
       
       # polling sanitize status in its log page
       nvme0.getlogpage(0x81, buf, 20).waitdone()
       while buf.data(3, 2) & 0x7 != 1:  # sanitize is not completed
           progress = buf.data(1, 0)*100//0xffff
           # display the progress of sanitize in a GUI window
           sg.OneLineProgressMeter('sanitize progress', progress, 100,
                                   'progress', orientation='h')
           nvme0.getlogpage(0x81, buf, 20).waitdone()
           time.sleep(1)


Ex3: parameterized tests
------------------------

.. code-block:: python

   # create a parameter with a argument list
   @pytest.mark.parametrize("qcount", [1, 2, 4, 8, 16])
   def test_ioworker_iops_multiple_queue(nvme0n1, qcount):
       l = []
       io_total = 0

       # create multiple ioworkers for read performance test
       for i in range(qcount):
           a = nvme0n1.ioworker(io_size=8, lba_align=8,
                                region_start=0, region_end=256*1024*8, # 1GB space
                                lba_random=False, qdepth=16,
                                read_percentage=100, time=10).start()
           l.append(a)

       # after all ioworkers complete, calculate the IOPS performance result
       for a in l:
           r = a.close()
           io_total += (r.io_count_read+r.io_count_nonread)
       logging.info("Q %d IOPS: %dK" % (qcount, io_total/10000))

       
Ex4: upgrade and reboot the drive
---------------------------------

.. code-block:: python

   # this test function is actually a utility to upgrade SSD firmware
   def test_download_firmware(nvme0, subsystem):
       # open the firmware binary image file
       filename = sg.PopupGetFile('select the firmware binary file', 'pynvme')
       if filename:
           logging.info("To download firmware binary file: " + filename)

           # download the firmware image to SSD
           nvme0.downfw(filename)

           # power cycle the SSD to activate the upgraded firmware
           subsystem.power_cycle()
                   

Ex5: write drive and monitor temperature
----------------------------------------

.. code-block:: python

   # a temperature calculation package
   from pytemperature import k2c
   
   def test_ioworker_with_temperature(nvme0, nvme0n1):
       smart_log = d.Buffer(512, "smart log")

       # start the ioworker for sequential writing in secondary process
       with nvme0n1.ioworker(io_size=256, lba_align=256,
                             lba_random=False, qdepth=16,
                             read_percentage=0, time=30):
           # meanwhile, monitor SMART temperature in primary process
           for i in range(40):
               nvme0.getlogpage(0x02, smart_log, 512).waitdone()
               
               # the K temperture from SMART log page
               ktemp = smart_log.data(2, 1)
               logging.info("temperature: %0.2f degreeC" % k2c(ktemp))
               time.sleep(1)
   

Ex6: multiple ioworkers on different namespaces and controllers
---------------------------------------------------------------

.. code-block:: python

   def test_multiple_controllers_and_namespaces():
       # address list of the devices to test
       addr_list = [b'3a:00.0', b'10.24.48.17']

       # create the list of controllers and namespaces
       nvme_list = [d.Controller(a) for a in addr_list]
       ns_list = [d.Namespace(n) for n in nvme_list]
   
       # operations on multiple controllers
       for nvme in nvme_list:
           logging.info("device: %s" % nvme.id_data(63, 24, str))
   
       # start multiple ioworkers
       ioworkers = {}
       for ns in ns_list:
           a = ns.ioworker(io_size=8, lba_align=8,
                           region_start=0, region_end=256*1024*8, # 1GB space
                           lba_random=False, qdepth=16,
                           read_percentage=100, time=10).start()
           ioworkers[ns] = a
   
       # test results of different namespaces
       for ns in ioworkers:
           r = ioworkers[ns].close()
           io_total = (r.io_count_read+r.io_count_nonread)
           logging.info("capacity: %u, IOPS: %.3fK" %
                        (ns.id_data(7, 0), io_total/10000))
   

Ex7: format and fused operations
--------------------------------

.. code-block:: python

   # fused operation is not directly supported by pynvme APIs
   def test_fused_operations(nvme0, nvme0n1):
       # format the namespace to 4096 block size. Use Namespace.format(), instead
       # of Controller.format(), for pynvme to update namespace data in the driver. 
       nvme0n1.format(4096)

       # create qpair and buffer for IO commands
       q = d.Qpair(nvme0, 10)
       b = d.Buffer()
       
       # separate compare and write commands
       nvme0n1.write(q, b, 8).waitdone()
       nvme0n1.compare(q, b, 8).waitdone()
   
       # implement fused compare and write operations with generic commands
       # Controller.send_cmd() sends admin commands,
       # and Namespace.send_cmd() here sends IO commands. 
       nvme0n1.send_cmd(5|(1<<8), q, b, 1, 8, 0, 0)
       nvme0n1.send_cmd(1|(1<<9), q, b, 1, 8, 0, 0)
       q.waitdone(2)
