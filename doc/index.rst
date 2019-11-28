pynvme: test NVMe devices in Python
===================================

The pynvme is a Python extension module. Users can test NVMe devices intuitively in Python scripts. It is designed for NVMe storage developers with performance considered. Integrated with third-party tools (e.g. vscode and pytest), pynvme provides a convenient and professional solution of NVMe testing.

**Quick Start in 3 Steps!**

1. Clone pynvme from GitHub: https://github.com/pynvme/pynvme
   
.. code-block:: shell

   git clone https://github.com/pynvme/pynvme

2. Build pynvme:

.. code-block:: shell

   cd pynvme
   ./install.sh

3. Run pynvme tests. It reports 4K read IOPS of your SSD in 10 seconds.

.. code-block:: shell

   make setup
   make test TESTS="driver_test.py::test_ioworker_iops_multiple_queue[1]"

In this document, we explain the design and usage of pynvme, and you can soon write your own Python scripts to test NVMe devices.


.. image:: logo.jpg
   :target: logo.jpg
   :alt: pynvme logo

         
.. toctree::
   :maxdepth: 2
   :caption: Table of Contents
   :hidden:
      
   intro
   install
   pytest
   vscode
   features
   examples
   development
   api
