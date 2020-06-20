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


Controller
----------

.. image:: ./pic/controller.png
   :target: ./pic/controller.png
   :alt: NVMe Controller from NVMe spec

To access the NVMe device, scripts have to create `Pcie` object first, and then create the `Controller` object from this `Pcie` object. It is required to close `Pcie` object when it is not used. For example:


.. code-block:: python

   import nvme as d
   pcie = d.Pcie('01:00.0')
   nvme0 = d.Controller(pcie)
   # ...
   pcie.close()
   

It uses Bus:Device:Function address to specify a PCIe DUT. Then, We can access NVMe registers and send admin commands to the NVMe device. 

.. code-block:: python

   csts = nvme0[0x1c]  # CSTS register, e.g.: '0x1'
   nvme0.setfeatures(0x7, cdw11=(15<<16)+15).waitdone()


NVMe Initialization
^^^^^^^^^^^^^^^^^^^

When creating controller object, pynvme implements a default initialization process defined in NVMe specification 7.6.1 (v1.4). However, scripts can define its own initialization function, which has one parameter `Controller`. Here is an example:

.. code-block:: python
   :emphasize-lines: 17

   def test_init_nvme_customerized(pcie):
       def nvme_init(nvme0):
           nvme0[0x14] = 0
           while not (nvme0[0x1c]&0x1) == 0: pass
           nvme0.init_adminq()
           nvme0[0x14] = 0x00460000
           nvme0[0x14] = 0x00460001
           while not (nvme0[0x1c]&0x1) == 1: pass
           nvme0.identify(d.Buffer(4096)).waitdone()
           nvme0.init_ns()
           nvme0.setfeatures(0x7, cdw11=0x00ff00ff).waitdone()
           nvme0.getfeatures(0x7).waitdone()
           aerl = nvme0.id_data(259)+1
           for i in range(aerl):
               nvme0.aer()
   
       nvme0 = d.Controller(pcie, nvme_init_func=nvme_init)
    
                
Admin Commands
^^^^^^^^^^^^^^

We set the feature number of queues (07h) above, and now we try to get the configuration data back with admin command `Controller.getfeatures()`.

.. code-block:: python

   nvme0.getfeatures(7)

Pynvme sends the commands asynchronously, and so we can sync and wait for the commands completion by API `Controller.waitdone()`.

.. code-block:: python

   nvme0.waitdone(1)

Also, `Controller.waitdone()` returns dword0 of the latest completion data structure. So, we can get the feature data in one line:

.. code-block:: python

   assert (15<<16)+15 == nvme0.getfeatures(0x7).waitdone()


Pynvme supports all mandatory admin commands defined in the NVMe spec, as well as most of the optional admin commands. 
                

Command Callback
^^^^^^^^^^^^^^^^

Scripts can specify one callback function for every command call. After the command completes, pynvme calls the specified callback function. Here is an example:   

.. code-block:: python

   def getfeatures_cb1(cpl):
       logging.info(cpl)
   nvme0.getfeatures(7, cb=getfeatures_cb1).waitdone()
   
   def getfeatures_cb2(cdw0, status1):
       logging.info(status1)
   nvme0.getfeatures(7, cb=getfeatures_cb2).waitdone()

Pynvme provides two forms of callback function.
1. single parameters: *cpl*. Pynvme shall pass the whole 16-byte completion data structure to the single parameter callback funciton. This is recommended form. 
2. two parameters: *cdw0* and *status1*. Pynvme shall pass the dword0 and higher 16-bit of dword2 of Completion Queue Entry to the two-parameter callback function. *status1* is a 16-bit integer, which includes both **Phase Tag** and Status Field. This is the obsoleted form for back-compatibility only. 
   
Identify Data
^^^^^^^^^^^^^

Here is an usual way to get controller's identify data:

.. code-block:: python

   buf = d.Buffer(4096, 'controller identify data')
   nvme0.identify(buf, 0, 1).waitdone()
   logging.info("model number: %s" % buf[24:63, 24])

Scripts shall call `Controller.waitdone()` to make sure the `buf` is filled by the NVMe device with identify data. Moving one step forward, because identify data is so frequently used, pynvme provides another API `Controller.id_data()` to get a field of the controller's identify data more easily:

.. code-block:: python

   logging.info("model number: %s" % nvme0.id_data(63, 24, str))
   logging.info("vid: 0x%x" % nvme0.id_data(1, 0))

It retrieves bytes from 24 to 63, and interpret them as a `str` object. If the third argument is omitted, they are interpreted as an `int`. Users can refer to NVMe specification to get the fields of the data. 


Generic Commands
^^^^^^^^^^^^^^^^

Pynvme provides API for all mandatory admin commands and most of the optional admin commands listed in the NVMe specification. However, pynvme also provides the API to send the generic admin commands, `Controller.send_cmd()`. This API can be used for:
1. pynvme un-supported admin commands,
2. Vendor Specific admin commands
3. illegal Admin Commands

.. code-block:: python

   nvme0.send_cmd(0xff).waitdone()
   
   def getfeatures_cb_2(cdw0, status1):
       logging.info(status1)
   nvme0.send_cmd(0xa, nsid=1, cdw10=7, cb=getfeatures_cb_2).waitdone()

   
Utility Functions
^^^^^^^^^^^^^^^^^

Besides admin commands, class `Controller` also provides some utility functions, such as `Controller.reset()` and `Controller.downfw()`. Please refer to the last chapter for the full list of APIs. 

.. code-block:: python

   nvme0.downfw('path/to/firmware_image_file')
   nvme0.reset()

Please note that, these utility functions are not NVMe admin commands, so we do not need to reap them by `Controller.waitdone()`. 


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

AER is a special NVMe admin command. It is not applicable to timeout setting. In default NVMe initialization process, pynvme sends only one AER command for those unexpected AER events during the test. However, scripts can replace this default initializaiton process with which sends more AER commands. When one AER completed during the test, a warning is raised, and scripts have to call one more `waitdone` and send one more AER command. Scripts can also give a callback function to any AER command which is the same as the usual command.

Here is an example of AER with sanitize operations. 

.. code-block:: python
   :emphasize-lines: 19-20

   def test_aer_with_multiple_sanitize(nvme0, nvme0n1, buf):  #L8
      if nvme0.id_data(331, 328) == 0:  #L9
          pytest.skip("sanitize operation is not supported")  #L10
          
      logging.info("supported sanitize operation: %d" % nvme0.id_data(331, 328))
      
      for i in range(3):
          nvme0.sanitize().waitdone()  #L13
          
          # check sanitize status in log page
          with pytest.warns(UserWarning, match="AER notification is triggered"):
              nvme0.getlogpage(0x81, buf, 20).waitdone()  #L17
              while buf.data(3, 2) & 0x7 != 1:  #L18
                  time.sleep(1)
                  nvme0.getlogpage(0x81, buf, 20).waitdone()  #L20
                  progress = buf.data(1, 0)*100//0xffff
                  logging.info("%d%%" % progress)
                   
          nvme0.waitdone()  # reap one more CQE for completed AER
          nvme0.aer()  # send one more AER for the next sanitize operation


AER completion is triggered when sanitize operation is finished. We can find the UserWarning for the AER notification in the test log below. The first AER command is sent by pynvme initialization process, while the remaining AER commands are sent by user scripts. 

.. code-block:: shell
   :emphasize-lines: 15, 18, 21

   cmd: sudo python3 -B -m pytest --color=yes --pciaddr=3d:00.0 'scripts/test_examples.py::test_aer_with_multiple_sanitize'
   
   ================================ test session starts =================================
   platform linux -- Python 3.8.3, pytest-5.4.2, py-1.8.1, pluggy-0.13.1
   rootdir: /home/cranechu/pynvme, inifile: pytest.ini
   plugins: cov-2.9.0
   collected 1 item                                                                     
   
   scripts/test_examples.py::test_aer_with_multiple_sanitize 
   ----------------------------------- live log setup -----------------------------------
   [2020-06-07 22:57:09.934] INFO script(65): setup random seed: 0xb56b1bda
   ----------------------------------- live log call ------------------------------------
   [2020-06-07 22:57:10.334] INFO test_aer_with_multiple_sanitize(580): supported sanitize operation: 2
   [2020-06-07 22:57:13.139] INFO test_aer_with_multiple_sanitize(592): 10%
   [2020-06-07 22:57:14.140] WARNING test_aer_with_multiple_sanitize(590): AER triggered, dword0: 0x810106, status1: 0x1
   [2020-06-07 22:57:14.140] INFO test_aer_with_multiple_sanitize(592): 100%
   [2020-06-07 22:57:16.967] INFO test_aer_with_multiple_sanitize(592): 10%
   [2020-06-07 22:57:17.968] WARNING test_aer_with_multiple_sanitize(590): AER triggered, dword0: 0x810106, status1: 0x1
   [2020-06-07 22:57:17.969] INFO test_aer_with_multiple_sanitize(592): 100%
   [2020-06-07 22:57:20.777] INFO test_aer_with_multiple_sanitize(592): 10%
   [2020-06-07 22:57:21.779] WARNING test_aer_with_multiple_sanitize(590): AER triggered, dword0: 0x810106, status1: 0x1
   [2020-06-07 22:57:21.780] INFO test_aer_with_multiple_sanitize(592): 100%
   PASSED                                                                         [100%]
   --------------------------------- live log teardown ----------------------------------
   [2020-06-07 22:57:21.782] INFO script(67): test duration: 11.848 sec
   
   
   ================================= 1 passed in 12.30s =================================


Multiple Controllers
^^^^^^^^^^^^^^^^^^^^

Users can create as many controllers as they have, even mixed PCIe devices with NVMe over TCP targets in the test.

.. code-block:: python

   nvme0 = d.Controller(b'01:00.0')
   nvme1 = d.Controller(b'03:00.0')
   nvme2 = d.Controller(b'10.24.48.17')
   nvme3 = d.Controller(b'127.0.0.1:4420')
   for n in (nvme0, nvme1, nvme2, nvme3):
       logging.info("model number: %s" % n.id_data(63, 24, str))

One script can be executed multiple times with different NVMe drives' BDF address in the command line.

.. code-block:: shell

   laptop:~▶ sudo python3 -m pytest scripts/cookbook.py::test_verify_partial_namespace -s --pciaddr=01:00.0
   laptop:~▶ sudo python3 -m pytest scripts/cookbook.py::test_verify_partial_namespace -s --pciaddr=02:00.0

   
Qpair
-----

In pynvme, we combine a Submission Queue and a Completion Queue as a Qpair. The Admin `Qpair` is created within the `Controller` object implicitly. However, we need to create IO `Qpair` explicitly for IO commands. We can specify the queue depth for IO Qpairs. Scripts can delete both SQ and CQ by calling `Qpair.delete()`.

.. code-block:: python

   qpair = d.Qpair(nvme0, 10)
   # ...
   qpair.delete()

   
Similar to Admin Commands, we use `Qpair.waitdone()` to wait IO commands complete.

Interrupt
^^^^^^^^^

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

The Qpair object is created with a Controller object. So, users create the Qpair after the Controller. On the other side, users should free Qpair before the Controller. We recommend to use pytest and its fixture `nvme0`. It always creates controller before qpairs, and deletes controller after any qpairs.

Qpair objects may be reclaimed by Python Garbage Collection, when they are not used in the script. So, qpairs would be deleted and qid would be reused. If you really want to keep qpairs alive, remember to keep their references, for example, in a list:

.. code-block:: python

   def test_create_many_qpairs(nvme0):
       qlist = []  # container to reference all qpairs
       for i in range(16):
           qlist.append(d.Qpair(nvme0, 8))
       del qlist   # delete all 16 qpairs


Namespace
---------

We can create a Namespace and attach it to a Controller. It is required to close `Namespace` object when it is not used. 

.. code-block:: python

   nvme0n1 = d.Namespace(nvme0, nsid=1)
   # ...
   nvme0n1.close()

   
.. image:: ./pic/controller.png
   :target: ./pic/controller.png
   :alt: NVMe Controller from NVMe spec

For most Client NVMe SSD, we only need to use the fixture `nvme0n1` to declare the single namespace. Pynvme also supports callback functions of IO commands.

.. code-block:: python
                
   def write_cb(cdw0, status1):
       nvme0n1.read(qpair, read_buf, 0, 1)
   nvme0n1.write(qpair, data_buf, 0, 1, cb=write_cb).waitdone(2)

In the above example, the waitdone() function-call reaps two commands. One is the write command, and the other is the read command which was sent in the write command's callback function. The function-call waitdone() polls commands Completion Queue, and the callback functions are called within this waitdone() function. 


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

We mentioned earlier that pynvme verifies data integrity on the fly of data IO. However, the controller is not responsible for checking the LBA of a Read or Write command to ensure any type of ordering between commands. See explanation from NVMe specification:

    For all commands which are not part of a fused operation (refer to section 4.12), or for which the write size is greater than AWUN, each command is processed as an independent entity without reference to other commands submitted to the same I/O Submission Queue or to commands submitted to other I/O Submission Queues. Specifically, the controller is not responsible for checking the LBA of a Read or Write command to ensure any type of ordering between commands. For example, if a Read is submitted for LBA x and there is a Write also submitted for LBA x, there is no guarantee of the order of completion for those commands (the Read may finish first or the Write may finish first). If there are ordering requirements between these commands, host software or the associated application is required to enforce that ordering above the level of the controller.

For example, when two IOWorkers write the same LBA simultaneously, the order of these writes is not defined. Similarly, in a read/write mixed IOWorker, when both read and write IO happen on the same LBA, their order is also not defined. So, it is impossible for host to determine the data content of the read.

To avoid data conflict, we can start IOWorkers one after another. Otherwise, when we have to start multiple IOWorkers in parallel, we can separate them to different LBA regions. Pynvme maintains a lock for each LBA, so within a single ioworker, pynvme can detect and resolve the LBA conflication mention above, and thus make the data verification possible and reliable in one ioworker. For those conflict-free scripts, we can enable the data verify by the fixture `verify`.

.. code-block:: python

   def test_ioworker_write_read_verify(nvme0n1, verify):
       assert verify
       
       nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=False,
                        region_start=0, region_end=100000
                        read_percentage=0, time=2).start().close()
   
       nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=False,
                        region_start=0, region_end=100000
                        read_percentage=100, time=2).start().close()


Another consideration on data verify is the memory space. During Namespace initialization, only if pynvme can allocate enough memory to hold the CRC data for each LBA, the data verify feature is enabled on this Namespace. Otherwise, the data verify feature cannot be enabled. Take a 512GB namespace for an example, it needs about 4GB memory space for CRC data. However, scripts can specify a limited scope to enable verify function with limited DRAM usage.

.. code-block:: python
   :emphasize-lines: 3-4

   def test_verify_partial_namespace(nvme0):
       region_end=1024*1024*1024//512  # 1GB space
       nvme0n1 = d.Namespace(nvme0, 1, region_end)
       assert True == nvme0n1.verify_enable(True)
   
       nvme0n1.ioworker(io_size=8,
                        lba_random=True,
                        region_end=region_end,
                        read_percentage=50,
                        time=30).start().close()


IOWorker
--------

It is inconvenient and expensive to send each IO command in Python scripts. Pynvme provides the low-cost high-performance `IOWorker` to send IOs in separated processes. IOWorkers make full use of multi-core CPU to improve IO test performance and stress. Scripts create the `IOWorker` object by API `Namespace.ioworker()`, and start it. Then scripts can do anything else, and finally close it to wait the IOWorker process finish and get its result data. Each IOWorker occupies one Qpair in runtime. Here is an IOWorker randomly writing 4K data for 2 seconds.

.. code-block:: python

   r = nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=True, 
                        read_percentage=0, time=2).start().close()
   logging.info(r)


Return Data
^^^^^^^^^^^

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
     - total write and other non-read IO in the IOWorker
   * - io_count_write
     - int
     - total write IO in the IOWorker
   * - mseconds
     - int
     - IOWorker duration in milli-seconds
   * - cpu_usage
     - int
     - the percentage of CPU time used by ioworker
   * - latency_max_us
     - int
     - maximum latency in the IOWorker, unit is micro-seconds
   * - latency_average_us
     - int
     - average latency in the IOWorker, unit is micro-seconds
   * - error
     - int
     - error code of the IOWorker

Here are ioworker's error code:

+  0: no erro
+ -1: generic error
+ -2: io_size is larger than MDTS
+ -3: io timeout
+ -4: ioworker timeout

  
Output Parameters
^^^^^^^^^^^^^^^^^

To get more result of the ioworkers, we should provide output parameters.

- output_io_per_second: when an empty list is provided to output_io_per_second, ioworker will fill the io count of every seconds during the whole test.
- output_percentile_latency: when a dict, whose keys are a series of percentiles, is provided to output_percentile_latency, ioworker will fill the latency of these percentiles as the values of the dict.
- output_cmdlog_list: when a list is provided, ioworker fills the last completed commands information. 
  
With these detail output data, we can test IOPS consistency, latency QoS, and etc. Here is an example: 

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

           
Concurrent
^^^^^^^^^^

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

                
We can even start IOWorkers on different Namespaces in one script:

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

                

Scripts can send NVMe commands accompanied with IOWorkers. In this example, the script monitors SMART temperature value while writing NVMe device in an IOWorker. 

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

Scripts can also make a reset or power operation when iowrokers are active. But before these kinds of operations, scripts need to wait for seconds before ioworkers are started. In these way, we can inject abnormal events into the IO workload like dirty power cycle. 

.. code-block:: python

   def test_power_cycle_dirty(nvme0n1, subsystem):
       with nvme0n1.ioworker(io_size=256, lba_align=256,
                             lba_random=False, qdepth=64,
                             read_percentage=0, time=30):
           time.sleep(10)
           subsystem.power_cycle()

           
Performance
^^^^^^^^^^^

The performance of `IOWorker` is super high and super consistent because pynvme is an user-space driver. We can use it extensively in performance tests and stress tests. For example, we can get the 4K read IOPS in the following script.

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


Input Parameters
^^^^^^^^^^^^^^^^

IOWorker can also accurately control the IO pressure by the input parameter `iops`. 

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

The result of the IOWorker shows that it tests for 7 seconds, and sends 1234 IOs in each second. In this way, we can measure the latency against different IOPS pressure.

Scripts can create an ioworker up to 24 hours. We can also specify different data pattern in the IOWorker with arguments pvalue and ptype, which are the same definition as that in class Buffer.

Scripts can send different size IO in an ioworker through parameter io_size, which accepts different types of input: int, range, list, and dict.

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


`lba_random` is the percentage of random IO, while `read_percentage` defines the percentage of read IO. `op_percentage` can specify any IO opcodes as the keys of the dict, and the values are the percentage of that IO. So, we can send any kind of IO commands in ioworker, like Trim, Write Zeroes, Compare, and even VU commands.

.. code-block:: python

   def test_ioworker_op_dict_trim(nvme0n1):
       nvme0n1.ioworker(io_size=2,
                        lba_random=30,
                        op_percentage={2: 40, 9: 30, 1: 30},
                        time=2).start().close()

For more details on these input parameters, please refer to the lastest chapter of API documents, we well as the examples in the file: https://github.com/pynvme/pynvme/blob/master/scripts/test_examples.py


Miscellaneous
-------------

Besides functions described above, pynvme provides more facilities to make your tests more simple and powerful.

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

Pynvme also supports third-party hardware power module. Users provides the function of poweron and poweroff when creating subsystem objects, and pynvme calls them in `Subsystem.poweron()` and `Subsystem.poweroff()`.

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

It is required to call `Controller.reset()` after `Subsystem.power_cycle()` and `Subssytem.poweron()`. 

   
Reset
^^^^^

Pynvme provides different ways of reset: 

.. code-block:: python

   nvme0.reset()     # reset controller by its CC.EN register. We can also reset the NVMe device as a PCIe device:
   
   pcie.reset()      # PCIe hot reset
   nvme0.reset()
   
   subsystem.reset() # use register NSSR.NSSRC
   nvme0.reset()

It is required to call `Controller.reset()` after `Pcie.reset()` and `Subsystem.reset()`.


Random Number
^^^^^^^^^^^^^

Before every test item, pynvme sets a different random seed to get different serie of random numbers. When user wants to reproduce the test with the identical random numbers, just manually set the random seed in the beginning of the test scripts. For example:

.. code-block:: python
   :emphasize-lines: 3

   def test_ioworker_iosize_inputs(nvme0n1):
       # reproduce the test with the same random seed, and thus the identical random numbers generated by host
       d.srand(0x58e7f337)
       
       nvme0n1.ioworker(io_size={1: 2, 8: 8}, time=1).start().close()
       

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

       
Pynvme opens quite many APIs of low-level resources, so people are free to make innovations with pynvme in user scripts. 
