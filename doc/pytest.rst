Pytest
======

Execution
---------

.. code-block:: shell

   make test
   make test TESTS=scripts
   make test TESTS=scripts/demo_test.py
   make test TESTS=scripts/utility_test.py::test_download_firmware

Fixtures
--------

Pynvme uses pytest to test it self. Users can also use pytest as the test framework to test their NVMe devices. Pytest's fixture is a powerful way to create and free resources in the test.

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

