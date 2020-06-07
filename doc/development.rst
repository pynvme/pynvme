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

The pynvme modified code is in the branch of pynvme_1.x. We will regularly rebase pynvme modifications to the latest SPDK/DPDK stable release. 

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

If you meet any problem, please report it to `Issues <https://github.com/pynvme/pynvme/issues>`_ with the *test.log* file uploaded.


Socket
------

Pynvme replaced Kernel's NVMe driver, so usual user space utilities (e.g. nvme-cli, iostat, etc) are not aware of pynvme and its tests. Pynvme provides an unix socket to solve these problems. Scripts and third-party tools can use this socket to get the current status of the testing device. Currently, we support 3 commands of jsonrpc call:

1. list_all_qpair: get the status of all created qpair, like its qid and current outstanding IO count.
2. get_iostat: get current IO performance of the testing device.
3. get_cmdlog: get the recent commands and completions in the specified qpair.

Here is an example of scripts access this socket in Python, but it can be accessed by any other tools (e.g. typescript which is used by pynvme's VSCode plugin).

.. code-block:: shell

   def test_jsonrpc_list_qpairs(pciaddr):  #L1
       import json
       import socket  #L3
   
       # create the jsonrpc client
       sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
       sock.connect('/var/tmp/pynvme.sock')  #L7
   
       def jsonrpc_call(sock, method, params=[]):  #L9
           # create and send the command
           req = {}
           req['id'] = 1234567890
           req['jsonrpc'] = '2.0'
           req['method'] = method
           req['params'] = params
           sock.sendall(json.dumps(req).encode('ascii'))
   
           # receive the result
           resp = json.loads(sock.recv(4096).decode('ascii'))
           assert resp['id'] == 1234567890
           assert resp['jsonrpc'] == '2.0'
           return resp['result']
   
       # create controller and admin queue
       nvme0 = d.Controller(d.Pcie(pciaddr))  #L25
       
       result = jsonrpc_call(sock, 'list_all_qpair')  #L27
       assert len(result) == 1  #L28
