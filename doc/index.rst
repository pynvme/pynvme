pynvme: test NVMe devices in Python
===================================

The pynvme is a python extension module. Users can operate NVMe SSD intuitively in Python scripts. It is designed for NVMe SSD testing with performance considered. Integrated with third-party tools, vscode and pytest, pynvme provides a convenient and professional solution to test NVMe devices.


**Quick Start in 3 Steps!**

1. Clone pynvme from GitHub: https://github.com/cranechu/pynvme
   
.. code-block:: shell

   git clone https://github.com/cranechu/pynvme

2. Build pynvme:

.. code-block:: shell

   cd pynvme
   ./install.sh

3. Run pynvme tests. It reports 4K read IOPS of your SSD in 10 seconds.

.. code-block:: shell

   make setup
   make test TESTS="driver_test.py::test_ioworker_iops_multiple_queue[1]"

In following chapters, we will explain the design and usage of pynvme, and soon you can write your own Python scripts to test NVMe devices.


.. image:: logo.jpg
   :target: logo.jpg
   :alt: pynvme logo

         
.. toctree::
   :maxdepth: 2
   :caption: Table of Contents

   intro
   install
   pytest
   vscode
   features
   examples
   development
   api
