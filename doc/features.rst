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
