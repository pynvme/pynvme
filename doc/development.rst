Development
===========

You are always warmly welcomed to join us to develop pynvme, as well as the test scripts, together! Here are some fundamental information for pynvme development.

Files
-----

Pynvme makes use a bunch of 3-rd party tools. Here is a collection of key source code and configuration files and directories.

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

Our official repository is at: https://github.com/pynvme/pynvme. We built pynvme based on SPDK/DPDK. In order to extend them with test-purpose features, we forked SPDK and DPDK respectively at:

- SPDK: https://github.com/cranechu/spdk
- DPDK: https://github.com/cranechu/dpdk

The pynvme modified code is in the branch of pynvme_1.x. We will regularly (e.g. every 6 months) rebase pynvme modifications to latest SPDK/DPDK stable release. 

CI
--

We defined 3 different tests for pynvme in GitLab's CI:

#. checkin test: it is executed automatically when any new commit pushed onto master or any other branches. It should be finished in 3 minutes.
#. stress test: it is executed automatically in every weekend. Furthermore, before we merge any code onto master, we should also start and pass this stress test. We can start it here: https://gitlab.com/cranechu/pynvme/pipeline_schedules. It should be finished in 3 hours. 
#. manual test: we can start any test scripts via web: https://gitlab.com/cranechu/pynvme/pipelines/new. For example, when we need to run performance tests, we can set variable key to "SCRIPT_PATH", and set its varaiable value to "scripts/performance". Then, CI starts the tests as below:
   
   .. code-block:: shell
   
      make test TESTS="scripts/performance"

We can find CI test status, logs and reports here: https://gitlab.com/cranechu/pynvme/pipelines.

The CI runner is setup on Fedora 30 Server. 


Debug
-----

#. assert: We leave a lot of assert in SPDK and pynvme code, and they are all enabled in the compile time by default. 
#. log: logs include driver's log and script's log. All logs are captured/hidden by pytest in default. You can find them in file *test.log* even in the run time of tests. Users can change log levels for driver and scripts. 

   #. driver: spdk_log_set_print_level in driver.c, for SPDK related logs. Set it to SPDK_LOG_DEBUG for more debug output, while it makes very heavy overhead. 
   #. scripts: log_cli_level in pytest.ini, for python/pytest scripts.

#. gdb: when driver crashes or any unexpected behave observed, we can collect debug information through gdb.

   #. core dump: sudo coredumpctl debug
   #. generate core dump in dead loop: CTRL-\\
   #. test within gdb (e.g. realgud with Emacs)
      
      .. code-block:: shell
                      
         sudo gdb --args python3 -m pytest --color=yes --pciaddr=01:00.0 "driver_test.py::test_create_device"

If you meet any issue, or have any suggestions, please report them to `Issues <https://github.com/pynvme/pynvme/issues>`_! Please attach the *test.log* file. 
