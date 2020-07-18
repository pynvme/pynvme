Pytest
======

The `pytest <https://pytest.org/en/latest/>`_ framework helps developers writing test scripts from simple to complex. Pynvme is integrated with pytest, but it can also be used standalone. 

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
     - the object of default NVMe controller
   * - nvme0n1
     - session
     - the object of first Namespace of the default controller
   * - verify
     - function
     - declare this fixture in test cases where data CRC is to be verified.

In the following example, the fixture *nvme0n1* initializes the namespace for the test. Then, we can use it to start an ioworker directly. Super intuitive! 

.. code-block:: python

   def test_ioworker_simplified_context(nvme0n1):
       with nvme0n1.ioworker(io_size=8, lba_align=16,
                             lba_random=True, qdepth=16,
                             read_percentage=0, time=2):
           pass

We no longer need to repeat nvme0n1 creation in every test case as usual way:

.. code-block:: python

   nvme0 = d.Controller(b'01:00.0')
   nvme0n1 = d.Namespace(nvme0, 1)

   
Execution
---------

With pytest and pre-defined makefile, we can execute tests in many flexible ways, like these: 

.. code-block:: shell

   # all tests under the directory
   make test TESTS=scripts

   # all tests in one file
   make test TESTS=scripts/demo_test.py

   # a specific test function
   make test TESTS=scripts/utility_test.py::test_download_firmware

   # a test function with a specified parameter
   make test TESTS="driver_test.py::test_ioworker_iops_multiple_queue[1]"

   # start tests on multiple drives with 1GB reserved memory space each
   make test TESTS=scripts/stress/endurance_test.py::test_replay_jedec_client_trace pciaddr=01:00.0   
   make test TESTS=scripts/stress/endurance_test.py::test_replay_jedec_client_trace pciaddr=02:00.0   
   make test TESTS=scripts/stress/endurance_test.py::test_replay_jedec_client_trace pciaddr=172.168.5.44
   
   
Without specified pciaddr commandline parameter, *make test* automatically uses the last PCIe NVMe device in the lspci list. Pynvme supports multiple test sessions with different NVMe devices, or even NVMe over TCP targets, specified in the command line.
