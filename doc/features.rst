Features
========

Users can pynvme to operate NVMe controllers, namespaces, PCI devices, data buffers and etc.

Buffer
------

In order to read and write data to NVMe devices, users need to allocate and provide the `Buffer` to these IO commands. In this example, it allocates a 512-byte buffer, and get identify data of the controller. We can also give a name to the buffer. 

.. code-block:: python

   buf = d.Buffer(512, "part of identify data")
   nvme.identify(buf).waitdone()
   # now, the buf contains the identify data
   print(buf[0:4])

Do not delete the `Buffer` before the commands who are using it complete, otherwise you memory would be corrupted.

data pattern
^^^^^^^^^^^^

Users can identify the data pattern of the buffer. Pynvme supports following different data patterns by specify argument `pvalue` and `ptype`.

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
     - 1
     - 32-bit data
   * - random data
     - 0xbeef
     - compression percentage rate

Pynvme fills the buffer according to the pattern specified during the `Buffer` initialization. Users can also specify argument `pvalue` and `ptype` in IOWorker in the same manner.

Controller
----------

.. image:: ./pic/controller.png
   :target: ./pic/controller.png
   :alt: NVMe Controller from NVMe spec

To operate the NVMe controller, users need to create the `Controller` object in the scripts, for example:

.. code-block:: python

   import nvme as d
   nvme0 = d.Controller(b'01:00.0')

It uses Bus:Device:Function address to specify a PCIe DUT. We can also provide the IP address to create a controller of NVMe over TCP target. 

We can access NVMe register in BAR space by its offset:

.. code-block:: python

   hex(nvme0[0x1c])  # CSTS register, e.g.: '0x1'

Admin Commands
^^^^^^^^^^^^^^

We can send admin commands like this:

.. code-block:: python

   nvme0.getfeatures(7)

Pynvme sends the commands asynchronously, and so we need to sync and wait the commands complete by API Controller.waitdone().

.. code-block:: python

   nvme0.waitdone(1)

Most of the time, we can send and reap one admin command in this form:

.. code-block:: python

   nvme0.getfeatures(7).waitdone()

Callback
^^^^^^^^

After one command completes, pynvme calls the callback we specified for that command. Here is an example:   

.. code-block:: python

       def write_cb(cdw0, status1):
           nvme0n1.read(qpair, read_buf, 0, 1)
       nvme0n1.write(qpair, data_buf, 0, 1, cb=write_cb).waitdone(2)

In the above example, the waitdone function call reaps two commands. One is the write command, the other the read command which was sent in write command's callback function. The function call waitdone() polls commands Completion Queue, and the callback functions are called within waitdone() function call. 

Pynvme provides two arguments to python callback functions: *cdw0* of the Completion Queue Entry, and the *status1*. The argument *status1* is a 16-bit integer, which includes both **Phase Tag** and Status Field.

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

Generic Commands
^^^^^^^^^^^^^^^^

We can send most of the admin commands listed in NVMe specification. Besides that, we can also send Vendor Specific admin commands, as well as any legal and illegal admin commands, through the generic API: Controller.send_cmd(): 

.. code-block:: python

   nvme0.send_cmd(0xff).waitdone()

Utitity Functions
^^^^^^^^^^^^^^^^^

By writing NVMe register CC.EN, we can reset the controller. Pynvme implemented it in API Controller.reset().

.. code-block:: python

   nvme0.reset()

Controller also provides more APIs for usual operations. For example, we can upgrade firmware in the script likt this way: 

.. code-block:: python

   nvme0.downfw('path/to/firmware_image_file')

Please note that, these utility APIs (`id_data`, `reset`, `downfw`, and etc) are not NVMe admin commands, so we do not need to reap them in Controller.waitdone(). 

Asynchorous Event Request
^^^^^^^^^^^^^^^^^^^^^^^^^

NVMe Admin command AER is somewhat special. Pynvme driver sends some AER commands during Controller initialization. When some error or event happens, one AER command completes to notify host driver for the unexpected error or event. And pynvme driver notifies the scripts by an aer callback function. In the example below, we use the pytest fixture `aer` to define the AER callback function. When an AER triggered by NVMe devices, this callback function will be called by pynvme. 

.. code-block:: python

   def test_sanitize(nvme0, nvme0n1, buf, aer):
       if nvme0.id_data(331, 328) == 0:
           warnings.warn("sanitize operation is not supported")
           return

       def cb(cdw0, status):
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

For NVMe Admin command Sanitize, an AER command should be completed. We can find the log information printed in the AER callback function below. 

.. code-block:: shell

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

Besides the log inforamtion printed in the AER callback function, we can also find an UserWarning for the AER notification. So, even if aer and aer callback function is not provided in scripts, pynvme can still highlight those unexpected errors and events. 

Timeout
^^^^^^^

The timeout is configurable, and the default time is 10 seconds. Users can change the timeout for those expected long-time commands.

.. code-block:: python

    nvme0.timeout=30000  # the unit is milli-second
    nvme0.format().waitdone()  # format may take long-time to complete
    nvme0.timeout=10000

Mutliple Controllers
^^^^^^^^^^^^^^^^^^^^

Users can creates as many controllers as they have, even mixed PCIe devcies with NVMe over TCP targets.

.. code-block:: python

   nvme0 = d.Controller(b'01:00.0')
   nvme1 = d.Controller(b'03:00.0')
   nvme2 = d.Controller(b'10.24.48.17')
   nvme3 = d.Controller(b'127.0.0.1:4420')
   for n in (nvme0, nvme1, nvm2, nvm3):
       logging.info("model number: %s" % n.id_data(63, 24, str))

Qpair
-----

In pynvme, we combine a Submission Queue and a Completion Queue as a Qpair. The Admin `Qpair` is created within the `Controller` object implicitly. However, we need to create IO `Qpair` explicitly for IO commands. We can specify the queue depth in the scripts. 

.. code-block:: python

   qpair = d.Qpair(nvme0, 10)

Similar to Admin commands, we use Qpair.waitdone() to wait IO commands completed.

Interrupts
^^^^^^^^^^

Pynvme creates the IO Completion Queues with interrupt enabled. However, pynvme does not check the interrupt signals. We can check interrupt signals through a set of API Qpair.msix_*(). Here is an example. 

.. code-block:: python

   q = d.Qpair(nvme0, 8)
   q.msix_clear()
   assert not q.msix_isset()
   nvme0n1.read(q, buf, 0, 1) # nvme0n1 is the Namespace of nvme0
   time.sleep(1)
   assert q.msix_isset()
   q.waitdone()

Interrupt is supported only for testing. Pynvme still reaps completions by polling, without the interrupt signal. Users can check the interrupt signal in test scripts when they need to test this part of function. The interrupt of Admin Qpair of the Controller is handles in a different way by pynvme, pynvme does check the interrupt signal in each Controller.waitdone() function call. Only when the interrupt of Admin commands is presented, pynvme would reap Admin Commands. Interrupts associated with the Admin Completion Queue should not be delayed (specified in 7.5 Interrupts, NVMe specification 1.4).

Cmdlog
^^^^^^

Pynvme traces recent thousands of commands in the cmdlog, as well as the completion entries. The cmdlog traces each qpair's commands and status. Pynvme supports up to 16 qpairs (including the admin qpair of the controller). API Qpair.cmdlog() lists the cmdlog of the Qpair. With pynvme's VSCode plugin, users can get the cmdlog in IDE's GUI. 

Notice
^^^^^^

Qpair instance is created based on Controller instance. So, user creates qpair after the controller. In the other side, user should free qpair before the controller. But without explicit code, Python may not garbage collect these objects in the right order. 

We recommend to use pytest in your tests. The fixture nvme0 is defined as session scope, and so it is always created before any Qpair, and deleted after any Qpair. 

Namespace
---------

We can create a `Namespace` and attach it to a `Controller`:

.. code-block:: python

   nvme0n1 = d.Namespace(nvme0, nsid=1)

.. image:: ./pic/controller.png
   :target: ./pic/controller.png
   :alt: NVMe Controller from NVMe spec

For most Client NVMe SSD, we only need to use the fixture `nvme0n1` to declare the single namespace. Similarly, pynvme supports callback functions of IO commands.

Generic Commands
^^^^^^^^^^^^^^^^

.. code-block:: python

   def test_invalid_io_command_0xff(nvme0n1):
       logging.info("controller0 namespace size: %d" % nvme0n1.id_data(7, 0))

As you see, we use API Namespace.id_data() to get a field of namespace identify data.

IO Commands
^^^^^^^^^^^

With `Namepace`, `Qpair`, and `Buffer`, we can send IO commnads to NVMe devices. 

.. code-block:: python

   def test_write_lba_0(nvme0, nvme0n1):
       buf = d.Buffer(512)
       qpair = d.Qpair(nvme0, 16)
       nvme0n1.write(qpair, buf, 0).waitdone()

Pynvme inserts LBA and calculates CRC data against each LBA block data to write. On the other side, pynvme checks LBA and CRC at reading, to verify the data integrity on the fly with ultra-low CPU cost. 

IOWorker
^^^^^^^^

It is inconvenient and expensive to send each IO command in Python scripts. Pynvme provides the low-cost high-performance `IOWorker` to send IOes in separated process. IOWorkers make full use of multi-core CPU to improve IO test performance and stress. Scripts create the `IOWorker` object by API Namespace.ioworker(), and start it. Then scripts can do anything else, and finally call close() method to wait the IOWorker completed and get the result data. Here is an IOWorker to randomly write 4K data for 2 seconds.

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
   * - io_count_write
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

We can start as many ioworkers as the IO Qpairs the NVMe device has.

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

And we can do other operations, accompanied with IOWorkers. In this example, the script monitors SMART temperature value while writing NVMe device in an IOWorker. 

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

The performance of `IOWorker` is super high and super consistent. We can use it to test performance. For example, we can get the 4K read IOPS in the following script.

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

Furthermore, we can also test IOPS consistency, latency QoS and distribution with IOWorkers. We can also specify different data pattern in the IOWorker.

IOWorker can accurately control the IO speed by the parameter `iops`. Here is an example test script: 

.. code-block:: python

   def test_ioworker_output_io_per_second(nvme0n1, nvme0):
       output_io_per_second = []
       nvme0n1.ioworker(io_size=8, lba_align=16,
                        lba_random=True, qdepth=16,
                        read_percentage=0, time=7,
                        iops=1234,
                        output_io_per_second=output_io_per_second).start().cIlose()
       logging.info(output_io_per_second)
       assert len(output_io_per_second) == 7
       assert output_io_per_second[0] != 0
       assert output_io_per_second[-1] >= 1233
       assert output_io_per_second[-1] <= 1235

The result of the IOWorker shows that it takes 7 seconds, and it sends 1234 IOes in each second. In this way, we can measure the latency againt different IOPS pressure. 

Data Verify
^^^^^^^^^^^

As we mentioned earlier that pynvme verifies data integrity on the fly of data IO. However, the controller is not responsible for checking the LBA of a Read or Write command to ensure any type of ordering between commands (NVMe spec 1.3c, 6.3). For example, when two IOWorkers write the same LBA simultanously, the order of these writes is not defined. Similarly, in a read/write mixed IOWorker, when both read and write IO happen on the same LBA, their order is also not defined. So, it is impossible for any host driver to determine the data content of read.

So, how we verify the data integrity in test scripts? We need to construct confliction-free IOWorkers with dedicated consideration. When we need to check the data integrity, and ensure that no data confliction could happen, we can specify the fixture `verify` to enable this pynvme feature.

.. code-block:: python

   def test_ioworker_write_read_verify(nvme0n1, verify):
       assert verify
       
       nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=False,
                        region_start=0, region_end=100000
                        read_percentage=0, time=2).start().close()
   
       nvme0n1.ioworker(io_size=8, lba_align=8, lba_random=False,
                        region_start=0, region_end=100000
                        read_percentage=100, time=2).start().close()

To avoid data confliction, we can start IOWorkers one after another. Otherwise, when we have to start multiple IOWorkers in parallel, we can separate them to different LBA regions. 

Another consideration on data verify is the memory space. During Namespace initialization, only if pynvme can allocate enough memory to hold the CRC data for each LBA, the data verify feature is enabled on this Namespace. Otherwise, the assert verify in above example should fail. Take a 512GB namespace for an example, it needs at least 4GB memory space for CRC data.

Trim
^^^^

Dataset Management (e.g. deallocate, or trim) is another commonly used IO command. It needs a prepared data buffer to identify LBA ranges to trim. Users can use API Buffer.set_dsm_range() for that. 

.. code-block:: python

   nvme0 = d.Controller(b'01:00.0')
   buf = d.Buffer(4096)
   qpair = d.Qpair(nvme0, 8)
   nvme0n1 = d.Namespace(nvme0)
   buf.set_dsm_range(0, 0, 8)
   buf.set_dsm_range(1, 8, 64)
   nvme0n1.dsm(qpair, buf, 2).waitdone()

PCIe
----

For those PCIe NVMe devices, we can access its PCI configuration space.

.. code-block:: python

   pcie = d.Pcie(nvme0)
   hex(pcie[0:4])  # Byte 0/1/2/3

Users can locate a specific capability by API Pcie.cap_offset(cap_id).    

.. code-block:: python

   pm_offset = pcie.cap_offset(1)  # Power Management Capability


Power
-----

Without any special hardware, pynvme makes use of S3 power state to power off the PCIe NVMe devices, and use RTC to wake and power on PCIe NVMe devices. We implemented it in API Subsystem.power_cycle().

.. code-block:: python

   subsystem = d.Subsystem(nvme0)
   subsystem.power_cycle(15)  # power off, sleep for 15 seconds, and power on

We can check if the hardware and OS supoprts S3 power state in the command line:

.. code-block:: shell

   > sudo cat /sys/power/state
   freeze mem disk
   > sudo cat /sys/power/mem_sleep
   s2idle [deep]

Reset
-----

We have Controller.reset() to reset controller by its CC.EN register. We can also reset the NVMe device as a PCIe device:

.. code-block:: python

   pcie.reset()

At last, we can reset the subsystem by writing NVMe register NSSR.NSSRC in API Subsystem.reset()


In the next chapter, let's read more real pynvme test scripts for find how we use pynvme in practical NVMe test.

In the last chapter, we can refer to the API document along with your script development. VSCode can also show you the online docstring when editing the code. 
