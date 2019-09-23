Pytest
======

The `pytest <https://pytest.org/en/latest/>`_ framework helps developers writing test scripts from simple to complex. Pynvme can be integrated with pytest.

Fixtures
--------

Pytest's fixture is a powerful way to create and free resources in the test. Pynvme provides following fixtures:

.. list-table::
   :header-rows: 1

   * - fixture
     - scope
     - notes
   * - pciaddr
     - session
     - PCIe BDF address of the DUT, pass in by argument --pciaddr
   * - pcie
     - session
     - the object of the PCIe device.
   * - nvme0
     - session
     - the object of NVMe controller
   * - nvme0n1
     - session
     - the object of first Namespace of the controller
   * - verify
     - function
     - declare this fixture in test cases where data crc is to be verified.

In the following example, the fixture *nvme0n1* initializes the namespace for the test. Then, we can use it to start an ioworker directly. Super intuitive! 

.. code-block:: python

   def test_ioworker_simplified_context(nvme0n1):
       with nvme0n1.ioworker(io_size=8, lba_align=16,
                             lba_random=True, qdepth=16,
                             read_percentage=0, time=2):
           pass

           
Execution
---------

With pytest, we execute tests in following ways.

.. code-block:: shell

   # all tests under the directory
   make test TESTS=scripts

   # all tests in one file
   make test TESTS=scripts/demo_test.py

   # a specific test function
   make test TESTS=scripts/utility_test.py::test_download_firmware

   # a test function with a specified parameter
   make test TESTS="driver_test.py::test_ioworker_iops_multiple_queue[1]"

*make test* automatically uses the first PCIe NVMe device in the test. We can also specify PCIe address of the NVMe device under test (DUT) in this command:

.. code-block:: shell

   sudo python3 -B -m pytest driver_test.py::test_ioworker_simplified_context --pciaddr=01:00.0

We can also actually specify the NVMe over TCP target in the same test:

.. code-block:: shell

   sudo python3 -B -m pytest driver_test.py::test_ioworker_simplified_context --pciaddr=10.24.48.17

Pynvme supports both PCIe and TCP NVMe devices. 
