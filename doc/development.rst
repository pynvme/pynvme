Development
===========

You are always warmly welcomed to join us to develop pynvme, as well as the test scripts, together! Here are some fundermental information for pynvme development.

Files
-----

Pynvme make use a bunch of 3-rd party tools. Here is a collection of key source code and configuration files and directories.

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
   * - .vscode
     - vscode configurations
   * - pynvme-console-1.x.x.vsix
     - pynvme plugin of VSCode
   * - requirements.txt
     - python packages required by pynvme
   * - .gitlab-ci.yml
     - pynvme's CI configuration file for gitlab.com
       

Repository
----------

Our offical repository is at: https://github.com/cranechu/pynvme. We built pynvme based on SPDK/DPDK. In order to extend them with test-purpose features, we forked SPDK and DPDK respectively at:

- SPDK: https://github.com/cranechu/spdk
- DPDK: https://github.com/cranechu/dpdk

The pynvme modified code is in the branch of pynvme_1.x. We will regularly (e.g. every 6 months) rebase pynvme modifications to latest stable SPDK/DPDK release. 

CI
--

For each commit, our CI run a quick test. Before merge any code to master, we should pass the stress test in CI. Here are pynvme's pipelines and jobs: https://gitlab.com/cranechu/pynvme/pipelines

Debug
-----

#. assert: We leave a lot of assert in SPDK and pynvme code, and they are all enabled in the compile time by default. 
#. log: logs include driver's log and script's log. All logs are captured/hidden by pytest in default. You can find them in file *test.log* even in the run time of tests. Users can change log levels for driver and scripts. 

   #. driver: spdk_log_set_print_level in driver.c, for SPDK related logs. Set it to SPDK_LOG_DEBUG for more debug output, while it makes very heavy overhead. 
   #. scripts: log_cli_level in pytest.ini, for python/pytest scripts.

#. gdb: when driver crashes or any misbehaviours happen, use can collect debug information through gdb.

   #. core dump: sudo coredumpctl debug
   #. generate core dump in dead loop: CTRL-\
   #. test within gdb (e.g. realgud with Emacs)
      
      .. code-block:: shell
                      
         sudo gdb --args python3 -m pytest --color=yes --pciaddr=01:00.0 "driver_test.py::test_create_device"

If you meet any issue, or have any suggestions, please report them to `Issues <https://github.com/cranechu/pynvme/issues>`_! Please attach the *test.log* file. 
