Introduction
============

Background
----------

Storage is important to client computers, data centers and enterprise servers. NVMe is a fast growing standard of storage in the era of Solid State Storage. However, most of the developers and users test NVMe devices by legacy utilities which are not designed for NVMe compatibility, performance, reliability and rapid evolution. On the other side, different kinds of storage materials have been developing in a fast and steady pace. Storage developers have to keep the same pace to develop products with latest storage technologies. In this condition, Agile development methodologies are widely adopted.

Testing in Agile development is very different from traditional development life cycle. It is no longer a standalone stage of the project. Instead, it is an important everyday practice in each stage of the project. So, we need a solid tool to support the NVMe testing. But, do we have the one?

We have great tools to test IO, for example, FIO and IOMeter. But IO is just a part of the storage features. We have some commercial softwares to test overall functions of NVMe devices, but they are not flexible to development, debug, and maintain test scripts. The testing infrastructure tool is always a frustrating **TODO** item in the backlogs.

Requirement
-----------

The most essential part of pynvme is a test dedicated driver, which shifts test in device-side to host-side. This driver should be:

1. lightweight. It exposes device functions, performance and issues to the host. We do not need file system nor cache between the raw devices and test scripts.
2. compact interface. We need an easy to use API, so developers can implement and maintain their test scripts easily.
3. high performance. NVMe is born with high performance, so is pynvme.
4. debug logs. We should keep enough debug information for both scripts developers and product developers, so they can investigate issues happened in the tests before blindly repeat the same tests.
5. automation. We need to make full use of modern software testing frameworks to improve the efficiency.

Design
------

We did not build pynvme from scratch. We build it based on the `SPDK <https://spdk.io/>`_, a reliable library of NVMe storage software stack. We extended SPDK NVMe driver with several testing-purpose functions in pynvme:

1. Interrupts. SPDK is a polling mode driver, so it does not support interrupts, like MSIx and MSI. We implemented a software interrupt host controller to enable and check interrupt signals.
2. Checksum. Storage cares data integrity. Pynvme verifies each LBA block with CRC32 checksum, without any penalty on performance.
3. Cmdlog. Pynvme traces every command and completion dwords. When any problem happens, users can examin the trace data to debug the issue.
4. IOWorker. It is too slow to send each IO in test scripts, so pynvme provides an agent to send IOes in separated processes. Users can create multiple IOWorkers with very low resource overhead. 

.. image:: pic/pynvme.png
   :target: pic/pynvme.png
   :alt: pynvme design
   
We then wrap all these SPDK and pynvme functions in a Python module. Users can use Python classes (e.g. Controller, Namespace, ...) to manage NVMe resources in the scripts, like this:

.. code-block:: python
                
   # create an NVMe controller with its PCIe address
   nvme0 = d.Controller(b"01:00.0")  

Now, let's install pynvme from source code before we dive into it. 
