Install
=======

Users can install and use pynvme in commodity computers.

System Requirement
------------------


#. CPU: x86_64.
#. OS: Linux.
#. Memory: 4GB or larger.
#. SATA: install OS and pynvme in a SATA drive.
#. NVMe: NVMe SSD is the device to be tested. Backup your data!
#. Python3: Python2 is not supported.
#. sudo privilege is required.
#. RAID mode (Intel® RST): should be disabled in BIOS.
#. Secure boot: should be disabled in BIOS.

Source Code
-----------

Fetch pynvme source code from GitHub, and simply run *install.sh* to build pynvme. *install.sh* generates the pynvme python package *nvme.cpython-37m-x86_64-linux-gnu.so*.

.. code-block:: shell

   git clone https://github.com/cranechu/pynvme
   cd pynvme
   git checkout tags/1.3  # opetional, checkout the latest stable release
   ./install.sh

Now, it is ready to `start vscode <#vscode>`_. Or, you can continue to refer to detailed installation instructions below.

Prerequisites
-------------

First, to fetch all required dependencies source code and packages.

.. code-block:: shell

   git submodule update --init --recursive
   sudo dnf install python3-pip -y # Ubuntu: sudo apt-get install python3-pip

Build
-----

Compile the SPDK, and then pynvme.

.. code-block:: shell

   cd spdk; ./configure --without-isal; cd ..   # configurate SPDK
   make spdk                                    # compile SPDK
   make                                         # compile pynvme

Now, you can find the generated binary file like: nvme.cpython-37m-x86_64-linux-gnu.so

Test
----

Setup SPDK runtime environment to remove kernel NVMe driver and enable SPDK NVMe driver. Now, we can run tests!

Before moving forward, check and backup your data in the NVMe SSD to be tested. It is always recommended to attach just one piece of NVMe SSD in your system to avoid mistakes.

.. code-block:: shell

   # backup your data in NVMe SSD before testing
   make setup
   make test
   make test TESTS=scripts
   make test TESTS=scripts/demo_test.py
   make test TESTS=scripts/utility_test.py::test_download_firmware

By default, it runs tests in driver_test.py. However, these are tests of pynvme itself, instead of SSD drives. Your DUT drive may fail in some test cases. Please add your tests in *scripts* directory.
Test logs are saved in file *test.log*. When you submit issues, please kindly attach this test.log file.

After test, you may wish to bring kernel NVMe driver back like this:

.. code-block:: shell

   make reset

User can find pynvme documents in README.md, or use help() in python:

.. code-block:: shell

   sudo python3 -c "import nvme; help(nvme)"  # press q to quit

