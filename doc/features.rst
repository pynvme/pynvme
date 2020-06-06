Features
========

In order to fully test NVMe devices for functionality, performance and even endurance, pynvme supports many features about NVMe controller, namespace, as well as PCIe and otheir essential parts in the system. 

PCIe
----

NVMe devices are firstly PCIe devices, so we need to management the PCIe resources. Pynvme can access NVMe device's PCI memory space and configuration space, including all capabilities.

.. code-block:: python

   pcie = d.Pcie('3d:00.0')
   hex(pcie[0:4])                  # Byte 0/1/2/3
   pm_offset = pcie.cap_offset(1)  # find Power Management Capability
   pcie.reset()
   pcie.aspm = 2                   # set ASPM control to enable L1 only
   pcie.power_state = 3            # set PCI PM power state to D3hot
   
Actually, pynvme can also test non-NVMe PCIe devices. 


Buffer
------

In order to transfer data with NVMe devices, users need to allocate and provide the `Buffer` to IO commands. In this example, it allocates a 512-byte buffer, and get identify data of the controller in this buffer. We can also give a name to the buffer. 

.. code-block:: python

   buf = d.Buffer(512, "part of identify data")
   nvme.identify(buf).waitdone()
   # now, the buf contains the identify data
   print(buf[0:4])
   del buf  # delete the `Buffer` after the commands complete.


data pattern
^^^^^^^^^^^^

Users can identify the data pattern of the `Buffer`. Pynvme supports following different data patterns by argument `pvalue` and `ptype`.

.. list-table::
   :header-rows: 1

   * - data pattern
     - ptype
     - pvalue  
   * - all 0
     - 0
     - 0
   * - all 1
     - 0
     - 1
   * - repeated dwords
     - 32
     - 32-bit data
   * - random data
     - 0xBEEF
     - compression percentage rate

Users can also specify argument `pvalue` and `ptype` in `Namespace.ioworker()` in the same manner.

The first 8-byte and the last 8-byte of each LBA are not filled by the data pattern. The first 8-byte is the LBA address, and the last 8-byte is a token which changes on every LBA written.

Python Space Drive
^^^^^^^^^^^^^^^^^^

Based on SPDK, pynvme provides a high performance NVMe driver for product test. However, it lacks of flexibility to test every details defined in the NVMe Specification. Here are some of the examples:

#. Multiple SQ share one CQ. Pynvme abstracts CQ and SQ as the Qpair.
#. Non-contiguous memory for SQ and/or CQ. Pynvme always allocates contiguous memory when creating Qpairs.
#. Complicated PRP tests. Pynvme creates PRP with some reasonable limitations, but it cannot cover all corner cases in protocol tests.

In order to cover these considerations, pynvme provides an extension of **Python Space Driver** (PSD). It is an NVMe driver implemented in pure Python based on two fundamental pynvme classes:

#. DMA memory allocation abstracted by class `Buffer`.
#. PCIe configuration and memory spaceprovided by class `Pcie`.

PSD implements NVMe data structures and operations in the module *scripts/psd.py* based on Buffer: 

#. PRP: alias of Buffer, and the size is the memory page by default.
#. PRPList: maintain the list of PRP entries, which are physical addresses of `Buffer`.
#. IOSQ: create and maintain IO Submission Queue.
#. IOCQ: create and maintain IO Completion Queue.
#. SQE: submission queue entry for NVMe commands dwords.
#. CQE: completion queue entry for NVMe completion dwords.

Here is an example: 

.. code-block:: python

   # import psd classes
   from psd import IOCQ, IOSQ, PRP, PRPList, SQE, CQE

   def test_send_cmd_2sq_1cq(nvme0):
       # 2 SQ share one CQ
       cq = IOCQ(nvme0, 1, 10, PRP())
       sq1 = IOSQ(nvme0, 1, 10, PRP(), cqid=1)
       sq2 = IOSQ(nvme0, 2, 16, PRP(), cqid=1)
   
       # write lba0, 16K data organized by PRPList
       write_cmd = SQE(1, 1)  # write to namespace 1
       write_cmd.prp1 = PRP() # PRP1 is a 4K page
       prp_list = PRPList()   # PRPList contains 3 pages
       prp_list[0] = PRP()
       prp_list[1] = PRP()
       prp_list[2] = PRP()
       write_cmd.prp2 = prp_list   # PRP2 points to the PRPList
       write_cmd[10] = 0           # starting LBA
       write_cmd[12] = 31          # LBA count: 32, 16K, 4 pages
       write_cmd.cid = 123;        # verify cid later
   
       # send write commands in both SQ
       sq1[0] = write_cmd          # fill command dwords in SQ1
       write_cmd.cid = 567;        # verify cid later
       sq2[0] = write_cmd          # fill command dwords in SQ2
       sq2.tail = 1                # ring doorbell of SQ2 first
       time.sleep(0.1)             # delay to ring SQ1, 
       sq1.tail = 1                #  so command in SQ2 should comple first
   
       # wait for 2 command completions
       while CQE(cq[1]).p == 0: pass
   
       # check first cpl
       cqe = CQE(cq[0])
       assert cqe.sqid == 2
       assert cqe.sqhd == 1
       assert cqe.cid == 567
   
       # check second cpl
       cqe = CQE(cq[1])
       assert cqe.sqid == 1
       assert cqe.sqhd == 1
       assert cqe.cid == 123
   
       # update cq head doorbell to device
       cq.head = 2
   
       # delete all queues
       sq1.delete()
       sq2.delete()
       cq.delete()


Controller
----------

.. image:: ./pic/controller.png
   :target: ./pic/controller.png
   :alt: NVMe Controller from NVMe spec

To operate the NVMe controller, users need to create the `Controller` object in the scripts, for example:

.. code-block:: python

   import nvme as d
   nvme0 = d.Controller(b'01:00.0')

It uses Bus:Device:Function address to specify a PCIe DUT. We can also provide the IP address to create the controller for the NVMe over TCP target. 

We can access NVMe registers dwords in BAR space by its offset:

.. code-block:: python

   csts = nvme0[0x1c]  # CSTS register, e.g.: '0x1'

Admin Commands
^^^^^^^^^^^^^^

We can send NVMe Admin Commands like this:

.. code-block:: python

   nvme0.getfeatures(7)

Pynvme sends the commands asynchronously, and so we need to sync and wait the commands complete by API `Controller.waitdone()``.

.. code-block:: python

   nvme0.waitdone(1)

Most of the time, we can send and reap one Admin Command in this form:

.. code-block:: python

   nvme0.getfeatures(7).waitdone()

Callback
^^^^^^^^

After one command completes, pynvme calls the callback we specified for that command. Here is an example:   

.. code-block:: python

   def getfeatures_cb(cdw0, status1):
       logging.info(status1)
   nvme0.getfeatures(7, cb=getfeatures_cb).waitdone()

Pynvme provides two arguments to python callback functions: *cdw0* of the Completion Queue Entry, and the *status1*. The argument *status1* is a 16-bit integer, which includes both **Phase Tag** and Status Field.
   
.. code-block:: python
                
   def write_cb(cdw0, status1):
       nvme0n1.read(qpair, read_buf, 0, 1)
   nvme0n1.write(qpair, data_buf, 0, 1, cb=write_cb).waitdone(2)

In the above example, the waitdone() function-call reaps two commands. One is the write command, and the other is the read command which was sent in the write command's callback function. The function-call waitdone() polls commands Completion Queue, and the callback functions are called within this waitdone() function. 


Identify Data
^^^^^^^^^^^^^

Here is an usual way to get controller's identify data:

.. code-block:: python

   buf = d.Buffer(4096, 'controller identify data')
   nvme0.identify(buf, 0, 1).waitdone()
   logging.info("model number: %s" % buf[24:63, 24])

Pynvme provides an API Controller.id_data() to get a field of the identify data:

.. code-block:: python

   logging.info("model number: %s" % nvme0.id_data(63, 24, str))

It retrieves bytes from 24 to 63, and interpret them as a `str` object. If the third argument is omitted, they are interpreted as an `int`.

.. code-block:: python
                
    logging.info("vid: 0x%x" % nvme0.id_data(1, 0))

Generic Commands
^^^^^^^^^^^^^^^^

We can send most of the Admin Commands listed in the NVMe specification. Besides that, we can also send Vendor Specific Admin Commands, as well as any legal and illegal Admin Commands, through the generic API `Controller.send_cmd()`: 

.. code-block:: python

   nvme0.send_cmd(0xff).waitdone()

We can specify more arguments for the generic Admin Commands, as well as the callback function:

.. code-block:: python

    def getfeatures_cb_2(cdw0, status1):
        logging.info(status1)
    nvme0.send_cmd(0xa, nsid=1, cdw10=7, cb=getfeatures_cb_2).waitdone()
    
Utility Functions
^^^^^^^^^^^^^^^^^

By writing NVMe register `CC.EN`, we can reset the controller. Pynvme implemented it in the API `Controller.reset()`.

.. code-block:: python

   nvme0.reset()

Controller also provides more APIs for usual operations. For example, we can upgrade firmware in the script like this: 

.. code-block:: python

   nvme0.downfw('path/to/firmware_image_file')

Please note that, these utility APIs (`id_data`, `reset`, `downfw`, and etc) are not NVMe Admin Commands, so we do not need to reap them by `Controller.waitdone()`. 

Timeout
^^^^^^^

The timeout duration is configurable, and the default time is 10 seconds. Users can change the timeout setting for those expected long-time consuming commands.

.. code-block:: python

    nvme0.timeout=30000  # the unit is milli-second
    nvme0.format().waitdone()  # format may take long time
    nvme0.timeout=10000  # recover to usual timeout configuration

When a command timeout happens, pynvme notifies user scripts in two ways. First, pynvme will throw a timeout warning. Second, pynvme completes (not abort) the command by itself with an all-1 completion dwords returned.     

Asynchronous Event Request
^^^^^^^^^^^^^^^^^^^^^^^^^^

NVMe Admin Command AER is somewhat special - they are not applicable to timeout. Pynvme driver sends some AER commands during the Controller initialization. When an error or event happen, one AER command completes to notify host driver for the unexpected error or event, and resend one more AER command. Then, pynvme driver notifies the scripts by AER command's callback function. In the example below, we use the pytest fixture `aer` to define the AER callback function. When an AER command completion is triggered by the NVMe device, this callback function will be called with arguments `cdw0` and `status1`, which is the same as the usual command's callback function.

.. code-block:: python
   :emphasize-lines: 5-7

   def test_sanitize(nvme0, nvme0n1, buf, aer):
       if nvme0.id_data(331, 328) == 0:
           pytest.skip("sanitize operation is not supported")

       def cb(cdw0, status1):
           logging.info("aer cb in script: 0x%x, 0x%x" % (cdw0, status))
       aer(cb)

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

For NVMe Admin command Sanitize, an AER command should be triggered. We can find the log information printed in the AER's callback function. Here is the output of the above test function. 

.. code-block:: shell
   :emphasize-lines: 18, 26
                     
   cwd: /home/cranechu/pynvme/
   cmd: sudo python3 -B -m pytest --color=yes --pciaddr=01:00.0 'scripts/utility_test.py::test_sanitize'

   ======================================= test session starts =======================================
   platform linux -- Python 3.7.3, pytest-4.3.1, py-1.8.0, pluggy-0.9.0 -- /usr/bin/python3
   cachedir: .pytest_cache
   rootdir: /home/cranechu/pynvme, inifile: pytest.ini
   plugins: cov-2.6.1
   collected 1 item                                                                                  

   scripts/utility_test.py::test_sanitize 
   ----------------------------------------- live log setup ------------------------------------------
   [2019-05-28 22:55:34.394] INFO pciaddr(19): running tests on DUT 01:00.0
   ------------------------------------------ live log call ------------------------------------------
   [2019-05-28 22:55:35.092] INFO test_sanitize(73): supported sanitize operation: 2
   [2019-05-28 22:55:35.093] INFO test_sanitize(74): sanitize, option 2
   [2019-05-28 22:55:41.288] WARNING test_sanitize(82): AER triggered, dword0: 0x810106
   [2019-05-28 22:55:41.289] INFO cb(70): aer cb in script: 0x810106, 0x1
   PASSED                                                                                      [100%]
   ---------------------------------------- live log teardown ----------------------------------------
   [2019-05-28 22:55:42.292] INFO script(33): test duration: 7.200 sec


   ======================================== warnings summary =========================================
   scripts/utility_test.py::test_sanitize
     /home/cranechu/pynvme/scripts/utility_test.py:82: UserWarning: AER notification is triggered
       nvme0.getlogpage(0x81, buf, 20).waitdone()

   -- Docs: https://docs.pytest.org/en/latest/warnings.html
   ============================== 1 passed, 1 warnings in 8.28 seconds ===============================

Besides the log information printed in the AER callback function, we can also find an UserWarning for the AER notification. So, even if AER and AER callback function is not provided in scripts, pynvme can still highlight those unexpected errors and events. 

Multiple Controllers
^^^^^^^^^^^^^^^^^^^^

Users can create as many controllers as they have, even mixed PCIe devices with NVMe over TCP targets.

.. code-block:: python

   nvme0 = d.Controller(b'01:00.0')
   nvme1 = d.Controller(b'03:00.0')
   nvme2 = d.Controller(b'10.24.48.17')
   nvme3 = d.Controller(b'127.0.0.1:4420')
   for n in (nvme0, nvme1, nvme2, nvme3):
       logging.info("model number: %s" % n.id_data(63, 24, str))

Qpair
-----

In pynvme, we combine a Submission Queue and a Completion Queue as a Qpair. The Admin `Qpair` is created within the `Controller` object implicitly. However, we need to create IO `Qpair` explicitly for IO commands. We can specify the queue depth for IO Qpairs. 

.. code-block:: python

   qpair = d.Qpair(nvme0, 10)

Similar to Admin Commands, we use `Qpair.waitdone()` to wait IO commands complete.

Interrupts
^^^^^^^^^^

Pynvme creates the IO Completion Queues with interrupt (e.g. MSIx or MSI) enabled. However, pynvme does not check the interrupt signals on IO Qpairs. We can check interrupt signals through a set of API `Qpair.msix_*()` in the scripts. Here is an example. 

.. code-block:: python

   q = d.Qpair(nvme0, 8)
   q.msix_clear()
   assert not q.msix_isset()
   nvme0n1.read(q, buf, 0, 1) # nvme0n1 is the Namespace of nvme0
   time.sleep(1)
   assert q.msix_isset()
   q.waitdone()

Interrupt is supported only for testing. Pynvme still reaps completions by polling, without checking the interrupt signals. Users can check the interrupt signal in test scripts when they need to test this function of the DUT. The interrupt of Admin Qpair of the Controller is handled in a different way by pynvme: pynvme does check the interrupt signals in each time of `Controller.waitdone()` function call. Only when the interrupt of Admin Commands is presented, pynvme would reap Admin Commands. Interrupts associated with the Admin Completion Queue cannot be delayed by coalescing (specified in 7.5 Interrupts, NVMe specification 1.4).

Cmdlog
^^^^^^

Pynvme traces recent thousands of commands in the cmdlog, as well as the completion dwords, for each Qpair. API `Qpair.cmdlog()` lists the cmdlog of the Qpair. With pynvme's VSCode plugin, users can also get the cmdlog in IDE's GUI windows. 

Notice
^^^^^^

The Qpair object is created on a Controller object. So, users create the Qpair after the Controller. On the other side, users should free Qpair before the Controller. Without explicit `del` in Python scripts, Python may not garbage collect these objects in the right order. We recommend to use pytest in your tests. The fixture `nvme0` is defined as session scope, and so the Controller is always created before any Qpair, and deleted after any Qpair.

Qpair objects may be reclaimed by Python Garbage Collection, when they are not used in the scripts. So, qpairs would be deleted implicitly. If you really want to keep qpairs alive, remember to keep their references as this example:

.. code-block:: python

   def test_create_many_qpairs(nvme0):
       qlist = []  # container to reference all qpairs
       for i in range(16):
           qlist.append(d.Qpair(nvme0, 8))
       del qlist   # delete all 16 qpairs


Namespace
---------

We can create a Namespace and attach it to a Controller:

.. code-block:: python

   nvme0n1 = d.Namespace(nvme0, nsid=1)

.. image:: ./pic/controller.png
   :target: ./pic/controller.png
   :alt: NVMe Controller from NVMe spec

For most Client NVMe SSD, we only need to use the fixture `nvme0n1` to declare the single namespace. Pynvme also supports callback functions of IO commands.

.. code-block:: python

   def test_invalid_io_command_0xff(nvme0n1):
       logging.info("controller0 namespace size: %d" % nvme0n1.id_data(7, 0))

As you see, we use API `Namespace.id_data()` to get a field of namespace identify data.


IO Commands
^^^^^^^^^^^

With `Namespace`, `Qpair`, and `Buffer`, we can send IO commands to NVMe devices. 

.. code-block:: python

   def test_write_lba_0(nvme0, nvme0n1):
       buf = d.Buffer(512)
       qpair = d.Qpair(nvme0, 16)
       nvme0n1.write(qpair, buf, 0).waitdone()

Pynvme inserts LBA and calculates CRC data for each LBA to write. On the other side, pynvme checks LBA and CRC data for each LBA to read. It verifies the data integrity on the fly with ultra-low CPU cost. 


Trim
^^^^

Dataset Management (e.g. deallocate, or trim) is another commonly used IO command. It needs a prepared data buffer to specify LBA ranges to trim. Users can use API `Buffer.set_dsm_range()` for that. 

.. code-block:: python

   nvme0 = d.Controller(b'01:00.0')
   buf = d.Buffer(4096)
   qpair = d.Qpair(nvme0, 8)
   nvme0n1 = d.Namespace(nvme0)
   buf.set_dsm_range(0, 0, 8)
   buf.set_dsm_range(1, 8, 64)
   nvme0n1.dsm(qpair, buf, 2).waitdone()


Generic Commands
^^^^^^^^^^^^^^^^

We can also send any IO commands through generic commands API `Namespace.send_cmd()`:

.. code-block:: python

    nvme0n1.send_cmd(5|(1<<8), q, b, 1, 8, 0, 0)
    nvme0n1.send_cmd(1|(1<<9), q, b, 1, 8, 0, 0)
    q.waitdone(2)

It is actually a fused operation of compare and write in the above script.

                
Data Verify
^^^^^^^^^^^

We mentioned earlier that pynvme verifies data integrity on the fly of data IO. However, the controller is not responsible for checking the LBA of a Read or Write command to ensure any type of ordering between commands (NVMe spec 1.3c, 6.3). For example, when two IOWorkers write the same LBA simultaneously, the order of these writes is not defined. Similarly, in a read/write mixed IOWorker, when both read and write IO happen on the same LBA, their order is also not defined. So, it is impossible for any host driver to determine the data content of read.

So, how we verify the data integrity in test scripts? We need to construct conflict-free IOWorkers with dedicated consideration. When we need to check the data integrity, and ensure that no data conflict could happen, we can specify the fixture `verify` to enable this feature.

.. code-block:: python

   def test_ioworker_write_read_verify(nvme0n1, verify):
       assert verify
       
       nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=False,
                        region_start=0, region_end=100000
                        read_percentage=0, time=2).start().close()
   
       nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=False,
                        region_start=0, region_end=100000
                        read_percentage=100, time=2).start().close()

To avoid data conflict, we can start IOWorkers one after another. Otherwise, when we have to start multiple IOWorkers in parallel, we can separate them to different LBA regions. 

Another consideration on data verify is the memory space. During Namespace initialization, only if pynvme can allocate enough memory to hold the CRC data for each LBA, the data verify feature is enabled on this Namespace. Otherwise, the data verify feature cannot be enabled. Take a 512GB namespace for an example, it needs at least 4GB memory space for CRC data.


IOWorker
--------

It is inconvenient and expensive to send each IO command in Python scripts. Pynvme provides the low-cost high-performance `IOWorker` to send IOs in separated process. IOWorkers make full use of multi-core CPU to improve IO test performance and stress. Scripts create the `IOWorker` object by API `Namespace.ioworker()`, and start it. Then scripts can do anything else, and finally close it to wait the IOWorker completed and get the result data. Each IOWorker occupies one Qpair. Here is an IOWorker to randomly write 4K data for 2 seconds.

.. code-block:: python

   r = nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=True, 
                        read_percentage=0, time=2).start().close()
   logging.info(r)

The IOWorker result data includes these information:

.. list-table::
   :header-rows: 1

   * - item
     - type
     - explanation
   * - io_count_read
     - int
     - total read IO in the IOWorker
   * - io_count_nonread
     - int
     - total write IO in the IOWorker
   * - mseconds
     - int
     - IOWorker duration in milli-seconds
   * - latency_max_us
     - int
     - maximum latency in the IOWorker, unit is micro-seconds
   * - error
     - int
     - error code of the IOWorker

To get more result of the ioworkers, we should provide arguments output_io_per_second and/or output_percentile_latency. When an empty list is provided to output_io_per_second, ioworker will fill the io count of every seconds during the whole test. When a dict, whose keys are a series of percentiles, is provided to output_percentile_latency, ioworker will fill the latency of these percentiles as the values of the dict. With these detail output data, we can test IOPS consistency, latency QoS, and etc. Here is an example: 

.. code-block:: python

   def test_ioworker_output_io_per_latency(nvme0n1, nvme0):
       output_io_per_second = []
       output_percentile_latency = dict.fromkeys([10, 50, 90, 99, 99.9, 99.99, 99.999, 99.99999])
       r = nvme0n1.ioworker(io_size=8, lba_align=8,
                            lba_random=False, qdepth=32,
                            read_percentage=0, time=10,
                            output_io_per_second=output_io_per_second,
                            output_percentile_latency=output_percentile_latency).start().close()
       assert len(output_io_per_second) == 10
       assert output_percentile_latency[99.999] < output_percentile_latency[99.99999]

We can simultaneously start as many ioworkers as the IO Qpairs NVMe device provides.

.. code-block:: python

   with nvme0n1.ioworker(lba_start=0, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=1000, time=0,
                         qprio=0, qdepth=9), \
        nvme0n1.ioworker(lba_start=1000, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=1000, time=0,
                         qprio=0, qdepth=9), \
        nvme0n1.ioworker(lba_start=8000, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=1000, time=0,
                         qprio=0, qdepth=9), \
        nvme0n1.ioworker(lba_start=8000, io_size=8, lba_align=64,
                         lba_random=False,
                         region_start=0, region_end=1000,
                         read_percentage=0,
                         iops=0, io_count=10, time=0,
                         qprio=0, qdepth=9):
       pass
   
We can even start IOWorkers on different Namespaces:

.. code-block:: python
   :emphasize-lines: 7

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

And we can also send other NVMe commands accompanied with IOWorkers. In this example, the script monitors SMART temperature value while writing NVMe device in an IOWorker. 

.. code-block:: python

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

However, pynvme does not support power_cycle or reset when IOWorkers are working. We have to close ioworkers first. 

.. code-block:: python

   def test_power_cycle_dirty(nvme0n1, subsystem):
       with nvme0n1.ioworker(io_size=256, lba_align=256,
                             lba_random=False, qdepth=64,
                             read_percentage=0, time=5):
           pass
       subsystem.power_cycle()
  
The performance of `IOWorker` is super high and super consistent. We can use it extensively in performance tests and stress tests. For example, we can get the 4K read IOPS in the following script.

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
           io_total += (r.io_count_read+r.io_count_nonread)

       logging.info("Q %d IOPS: %dK" % (qcount, io_total/10000))

       
IOWorker can accurately control the IO speed by the parameter `iops`. Here is an example test script: 

.. code-block:: python
   :emphasize-lines: 6

   def test_ioworker_output_io_per_second(nvme0n1, nvme0):
       output_io_per_second = []
       nvme0n1.ioworker(io_size=8, lba_align=16,
                        lba_random=True, qdepth=16,
                        read_percentage=0, time=7,
                        iops=1234,
                        output_io_per_second=output_io_per_second).start().close()
       logging.info(output_io_per_second)
       assert len(output_io_per_second) == 7
       assert output_io_per_second[0] != 0
       assert output_io_per_second[-1] >= 1233
       assert output_io_per_second[-1] <= 1235

The result of the IOWorker shows that it takes 7 seconds, and it sends 1234 IOs in each second. In this way, we can measure the latency against different IOPS pressure.

We can create an ioworker up to 24 hours. We can also specify different data pattern in the IOWorker with arguments pvalue and ptype, which are the same definition as that in class Buffer.

We can send different size IO in an ioworker through parameter io_size, which accepts different types of input: int, range, list, and dict.

.. list-table::
   :header-rows: 1

   * - type
     - explanation
     - example
   * - int
     - fixed io size
     - 1, send all io with size of 512 Byte. 
   * - range
     - a range of different io size
     - range(1, 8), send io size of 512, 1024, 1536, 2048, 2560, 3072, and 3584. 
   * - list
     - a list of different io size
     - [8, 16],  send io size of 4096, and 8192.
   * - dict
     - identify io size, as well as the ratio
     - {8: 2, 16: 1}, send io size of 4096 and 8192, and their IO count ratio is 2:1. 

We can limit ioworker sending IO in a region specified by parameter `region_start` and `region_end`. Furthermore, we can do a further fine granularity control of IO distribution across the LBA space by parameter `distribution`. It evenly divides LBA space into 100 regions, and we specify how to identify 10000 IOs in these 100 regions.

Here is an example to display how ioworker implements JEDEC workload by these parameters:

.. code-block:: python
                
   def test_ioworker_jedec_workload(nvme0n1):
       # distribute 10000 IOs to 100 regions
       distribution = [1000]*5 + [200]*15 + [25]*80
       
       # specify different IO size and their ratio of io count
       iosz_distribution = {1: 4,
                            2: 1,
                            3: 1,
                            4: 1,
                            5: 1,
                            6: 1,
                            7: 1,
                            8: 67,
                            16: 10,
                            32: 7,
                            64: 3,
                            128: 3}

       # implement JEDEC workload in a single ioworker
       nvme0n1.ioworker(io_size=iosz_distribution,
                        lba_random=True,
                        qdepth=32,
                        distribution = distribution,
                        read_percentage=0,
                        ptype=0xbeef, pvalue=100, 
                        time=10).start().close()



Misc
----

Power
^^^^^

Without any addtional equipment, pynvme can power off NVMe devices through S3 power state, and use RTC to wake it up. We implemented this process in API `Subsystem.power_cycle()`.

.. code-block:: python

   subsystem = d.Subsystem(nvme0)
   subsystem.power_cycle(15)  # power off, sleep for 15 seconds, and power on

We can check if the hardware and OS supports S3 power state in the command line:

.. code-block:: shell

   > sudo cat /sys/power/state
   freeze mem disk
   > sudo cat /sys/power/mem_sleep
   s2idle [deep]

Scripts can send a notification to NVMe device before turn power off, and this is so-called clean power cycle in SSD testing:

.. code-block:: python

   subsystem = d.Subsystem(nvme0)
   subsystem.shutdown_notify()
   subsystem.power_cycle()

Pynvme also supports third-party hardware power module. Users provides the function of poweron and poweroff when creating subsystem objects, and pynvme calls them in Subsystem.poweron() and Subsystem.poweroff().

.. code-block:: python

   def test_quarch_defined_poweron_poweroff(nvme0):
       import quarchpy
   
       def quarch_poweron():
           logging.info("power off by quarch")
           pwr = quarchpy.quarchDevice("SERIAL:/dev/ttyUSB0")
           pwr.sendCommand("run:power up")
           pwr.closeConnection()
   
       def quarch_poweroff():
           logging.info("power on by quarch")
           pwr = quarchpy.quarchDevice("SERIAL:/dev/ttyUSB0")
           pwr.sendCommand("signal:all:source 7")
           pwr.sendCommand("run:power down")
           pwr.closeConnection()
   
       s = d.Subsystem(nvme0, quarch_poweron, quarch_poweroff)

It is required to call Controller.reset() after Subsystem.power_cycle() and Subssytem.poweron(). 

   
Reset
^^^^^

Pynvme provides different ways of reset: 

.. code-block:: python

   nvme0.reset()     # reset controller by its CC.EN register. We can also reset the NVMe device as a PCIe device:
   
   pcie.reset()      # PCIe hot reset
   nvme0.reset()
   
   subsystem.reset() # use register NSSR.NSSRC
   nvme0.reset()

It is required to call Controller.reset() after Pcie.reset() and Subsystem.reset(). 

Random Number
^^^^^^^^^^^^^

Before every test item, pynvme sets a different random seed to get different serie of random numbers. When user wants to reproduce the test with the identical random numbers, just manually set the random seed in the beginning of the test scripts. For example:

.. code-block:: python
   :emphasize-lines: 3

   def test_ioworker_iosize_inputs(nvme0n1):
       # reproduce the test with the same random seed, and thus the identical random numbers generated by host
       d.srand(0x58e7f337)
       
       nvme0n1.ioworker(io_size={1: 2, 8: 8}, time=1).start().close()
       
