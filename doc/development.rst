Development
===========

Files
-----

Here is a brief introduction on key source code files.

.. list-table::
   :header-rows: 1

   * - files
     - notes
   * - spdk
     - pynvme is built on SPDK
   * - driver_wrap.pyx
     - pynvme uses cython to bind python and C. All python classes are defined here.
   * - cdriver.pxd
     - interface between python and C
   * - driver.h
     - interface of C
   * - driver.c
     - the core part of pynvme, which extends SPDK for test purpose
   * - setup.py
     - cython configuration for compile
   * - Makefile
     - it is a part of SPDK makefiles
   * - driver_test.py
     - pytest cases for pynvme test. Users can develop more test cases for their NVMe devices.
   * - conftest.py
     - predefined pytest fixtures. Find more details below.
   * - pytest.ini
     - pytest runtime configuration
   * - install.sh
     - build pynvme for the first time

Repository
----------

Our offical repository is at: https://github.com/cranechu/pynvme. We built pynvme based on SPDK/DPDK. And in order to extend them with test-purpose features, we forked SPDK and DPDK respectively at:

- SPDK: https://github.com/cranechu/spdk
- DPDK: https://github.com/cranechu/dpdk

The pynvme modified code is in the branch of pynvme_1.x. We will regularly (e.g. every 6-month) rebase pynvme modifications to latest stable SPDK/DPDK release. 

Debug
-----

#. assert: it is recommended to compile SPDK with --enable-debug.
#. log: users can change log levels for driver and scripts. All logs are captured/hidden by pytest in default. Please use argument "-s" to print logs in test time.

   #. driver: spdk_log_set_print_level in driver.c, for SPDK related logs
   #. scripts: log_cli_level in pytest.ini, for python/pytest scripts

#. gdb: when driver crashes or misbehaviours, use can collect debug information through gdb.

   #. core dump: sudo coredumpctl debug
   #. generate core dump in dead loop: CTRL-\
   #. test within gdb (e.g. realgud with Emacs)
      
      .. code-block:: shell
                      
         sudo gdb --args python3 -m pytest --color=yes --pciaddr=01:00.0 "driver_test.py::test_create_device"

If you meet any issue, or have any suggestions, please report them to `Issues <https://github.com/cranechu/pynvme/issues>`_. They are warmly welcome.

