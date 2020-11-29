Install
=======

All-in-One
----------

Users can build pynvme by simply running *install.sh* after getting source code from github. This is the recommended method to compile pynvme.

.. code-block:: shell

   git clone https://github.com/pynvme/pynvme
   cd pynvme
   ./install.sh
   
Now, it generates binary python module *nvme.so*. Users can import it in Python scripts:

.. code-block:: python

   import nvme as d
   nvme0 = d.Controller(d.Pcie("01:00.0"))
   
We will describe more details of installation below. You can skip to the next chapter if you have already got the binary *nvme.so*.

System Requirements
-------------------

Pynvme is a software-defined NVMe test solution, so users can install and use pynvme in most of the commodity computers with some requirements:

#. CPU: Intel x86_64, 4-core or more.
#. Memory: 4GB or larger.
#. OS: Linux. Fedora is recommanded. 
#. Python3: Python2 is not supported.
#. sudo privilege is required.
#. NVMe: NVMe SSD is the devices to be tested. Backup your data!
#. RAID mode (Intel® RST): shall be disabled in BIOS.
#. Secure boot: shall be disabled in BIOS.
#. IOMMU: (a.k.a. VT for Direct I/O) shall be disabled in BIOS.
#. VMD: shall be disabled in BIOS.
#. NUMA: recommend to be disabled in BIOS.
#. SATA: recommend to install OS and pynvme in a SATA drive.

   
Source Code
-----------

We clone the pynvme source code from GitHub. We recommend to checkout the latest stable release. 

.. code-block:: shell

   git clone https://github.com/pynvme/pynvme
   cd pynvme
   git checkout tags/2.3.0

Or you can clone the code from the mirror repository:

.. code-block:: shell

   git clone https://gitee.com/pynvme/pynvme

                
Prerequisites
-------------

Then, we need to fetch all required dependencies. 

.. code-block:: shell

   # fedora-like
   sudo dnf install -y make redhat-rpm-config python3-devel python3-pip

   # ubuntu-like
   sudo apt install -y python3-setuptools python3-dev python3-pip 

   # get SPDK and its submodules
   git submodule update --init --recursive

   # install SPDK required packages
   sudo ./spdk/scripts/pkgdep.sh

   # install python packages required by pynvme
   sudo python3 -m pip install -r requirements.txt

   
SPDK
----

We need to compile and test SPDK first. 

.. code-block:: shell

   # use the according pynvme-modified SPDK code
   cd spdk
   git checkout pynvme_2.3

   # configure SPDK
   ./configure --without-isal;

   # compile SPDK
   cd ..   
   make spdk

   # compile pynvme
   make

Now, we can find a generated binary file *nvme.so*.

Test
----
                
After compilation, let's first verify if SPDK works in your platform with SPDK applications. Before moving forward, check and backup your data in the NVMe SSD.

.. code-block:: shell

   # setup SPDK runtime environment             
   make setup

   # run pre-built SPDK application
   sudo ./identify_nvme

This application lists identify data of your NVMe SSD. If it works, let's move ahead to run pynvme tests!

.. code-block:: shell

   cd ~/pynvme
   make setup
   make test TESTS="driver_test.py::test_ioworker_iops_multiple_queue[1]"

After the test, we can find the file *test.log* in pynvme directory, which keeps more debug logs than that in the standard output. When you meet any problem, please submit issues with this *test.log*. 

*make setup* allocates hugepages and reserves NVMe devices for SPDK runtime environment. When you want to release memory and NVMe devices back to kernel, execute this command:

.. code-block:: shell

   make reset

pip
---

As an alternative way, we can also install pynvme with pip in the latest Fedora Linux. 

.. code-block:: shell
 
   pip install pynvme
   cd /usr/local/pynvme
   make setup
   make test TESTS="driver_test.py::test_ioworker_iops_multiple_queue[1]"

It installs a prebuilt pynvme binary module. But we still recommend to clone pynvme source code and compile it by *install.sh*.
