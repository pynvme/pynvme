Introduction
============

Background
----------

Storage is important to both client computers, data centers and enterprise servers. NVMe is a fast growing statndard of storage in the era of Solid State Storage. However, most of the developers and users test NVMe devices by legacy utilities, which are not designed for NVMe compatibilites, performance, reliability and rapid evolution.

On the other side, the NAND, as well as other storage materials, have been developing in a fast and steady pace. Storage deveopers have to keep the same pace to develop products based on latest storage chips.

Applications are changing. Ttechnologies are changing. They force storage developers to iterate their product design swiftly, thus Agile development methodology is adopt widely. Testing in Agile development is differnt from traditional develop way. It is no longer a standalone stage of the project. Instead, it is an important everyday practice in each stage of the project. So, we need a solid tool for NVMe testing. But, do we have it?

We have great tools to test IO, for example, FIO and IOMeter. But IO is just a part of the storage products. We have some commencial softwares to test different functions of NVMe, but we cannot implement our own test design in an efficient way. The testing infrustructure tool is always a frustrating item in the backlogs.

Requirement
-----------

We decided to develop *pynvme* for NVMe testing. The core part of pynvme is a testing dedicated driver, which moves tests in devices to the hosts. The driver should be:

1. lightweighted. It exposes device functions, performance and issues to the host. We do not need file system nor cache between the raw devices and test scripts.
2. compact interface. We need an easy to use API, so developers can implement and change their test scripts quickly.
3. performance. NVMe is born with high performance, so is pynvme.
4. logs. We should keep enough logs for both scripts developers and firmware developers, so they can investigate issues happened in the tests before blindly repeat the same tests.
5. automation. We need to make full use of modern software testing frameworks and tools, to improve the efficent of storage testing.

The pynvme is a python extension module. Users can operate NVMe SSD intuitively in Python scripts. It is designed for NVMe SSD testing with performance considered. Integrated with third-party tools, vscode and pytest, pynvme provides a convenient and professional solution to test NVMe devices.

Design
------

We do not build pynvme from scratch. We build the reliable tool based on the reliable library: the `SPDK <https://spdk.io/>`_. We extended SPDK nvme driver with several testing-purpose functions:

1. Interrupts. SPDK is a polling mode driver, so it does not support interrupts, like MSIx and MSI. We implemented a software interrupt host controller.
2. Checksum. Storage cases the integrity of data. Pynvme calculates crc32 when writing each LBA block, and verifies it when reading.
3. Cmdlog. Pynvme tracks every command, as well as its completion, sent by the scripts. When any problem happens, we can exam the trace information in the cmdlogs.
4. Ioworker. It is too slow to send each IO in test scripts, so we provide this agent to send IO in separated processes.

.. image:: pic/pynvme.png
   :target: pic/pynvme.png
   :alt: pynvme design
   
We then wrap all these SPDK and pynvme functions in a Python module. So, users can use Python classes (e.g. Controller, Namespace, ...) in the scripts like this:

.. code-block:: python
                
   # create an NVMe controller with its PCIe address
   nvme0 = d.Controller(b"01:00.0")  

Now, let's install pynvme first.    
