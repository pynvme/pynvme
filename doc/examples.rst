Examples
========

In this chapter, we will learn pynvme scripts with examples.

Ex1: hello world
----------------

.. code-block:: python

   import pytest
   import nvme as d
   
   def test_hello_world(nvme0, nvme0n1:d.Namespace):
       read_buf = d.Buffer(512)
       data_buf = d.Buffer(512)
       data_buf[10:21] = b'hello world'
       qpair = d.Qpair(nvme0, 16) 
   
       def write_cb(cdw0, status1):
           nvme0n1.read(qpair, read_buf, 0, 1)
       nvme0n1.write(qpair, data_buf, 0, 1, cb=write_cb)
       qpair.waitdone(2)
       assert read_buf[10:21] == b'hello world'


Ex2: sanitize
-------------

.. code-block:: python
                
   def test_sanitize(nvme0, nvme0n1, buf):
       if nvme0.id_data(331, 328) == 0:
           warnings.warn("sanitize operation is not supported")
           return
   
       logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))
       nvme0.sanitize().waitdone()
       
       # sanitize status log page
       nvme0.getlogpage(0x81, buf, 20).waitdone()
       while buf.data(3, 2) & 0x7 != 1:  # sanitize is not completed
           progress = buf.data(1, 0)*100//0xffff
           sg.OneLineProgressMeter('sanitize progress', progress, 100,
                                   'progress', orientation='h')
           nvme0.getlogpage(0x81, buf, 20).waitdone()
           time.sleep(1)


Ex3: parameterized tests
------------------------

.. code-block:: python

   @pytest.mark.parametrize("qcount", [1, 2, 4, 8, 16])
   def test_ioworker_iops_multiple_queue(nvme0n1, qcount):
       l = []
       io_total = 0
       for i in range(qcount):
           a = nvme0n1.ioworker(io_size=8, lba_align=8,
                                region_start=0, region_end=256*1024*8, # 1GB space
                                lba_random=False, qdepth=16,
                                read_percentage=100, time=10).start()
           l.append(a)
   
       for a in l:
           r = a.close()
           io_total += (r.io_count_read+r.io_count_write)
   
       logging.info("Q %d IOPS: %dK" % (qcount, io_total/10000))

       
Ex4: upgrade and reboot the drive
---------------------------------

.. code-block:: python

   import PySimpleGUI as sg
   
   def test_download_firmware(nvme0, subsystem):
       filename = sg.PopupGetFile('select the firmware binary file', 'pynvme')
       if filename:        
           logging.info("To download firmware binary file: " + filename)
           nvme0.downfw(filename)
           subsystem.power_cycle()
                   

Ex5: write drive and monitor temperature
----------------------------------------

.. code-block:: python
   
   from pytemperature import k2c
   
   def test_ioworker_with_temperature(nvme0, nvme0n1):
       smart_log = d.Buffer(512, "smart log")
       with nvme0n1.ioworker(io_size=8, lba_align=16,
                             lba_random=True, qdepth=16,
                             read_percentage=0, time=30):
           for i in range(40):
               nvme0.getlogpage(0x02, smart_log, 512).waitdone()
               ktemp = smart_log.data(2, 1)
               logging.info("temperature: %0.2f degreeC" % k2c(ktemp))
               time.sleep(1)
   

Ex6: two ioworkers on different namespaces
------------------------------------------

.. code-block:: python

   def test_two_namespace_ioworkers(nvme0n1, nvme0):
       nvme1 = d.Controller(b'03:00.0')
       nvme1n1 = d.Namespace(nvme1)
       with nvme0n1.ioworker(io_size=8, lba_align=16,
                             lba_random=True, qdepth=16,
                             read_percentage=0, time=100), \
            nvme1n1.ioworker(io_size=8, lba_align=16,
                             lba_random=True, qdepth=16,
                             read_percentage=0, time=100):
           pass
   

Ex7: format and fused operations
--------------------------------

.. code-block:: python

   def test_fused_operations(nvme0, nvme0n1):
       # LBA format: 4096 block size
       nvme0n1.format(4096)
   
       q = d.Qpair(nvme0, 10)
       b = d.Buffer()
       
       # compare and write
       nvme0n1.write(q, b, 8).waitdone()
       nvme0n1.compare(q, b, 8).waitdone()
   
       # fused compare and write with generic commands
       nvme0n1.send_cmd(5|(1<<8), q, b, 1, 8, 0, 0)
       nvme0n1.send_cmd(1|(1<<9), q, b, 1, 8, 0, 0)
       q.waitdone(2)
