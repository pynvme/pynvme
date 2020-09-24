pynvme: builds your own tests.
==============================

Pynvme is an user-space NVMe test driver with Python API. It is an open, fast, and extensible solution for SSD developers and test engineers to build their own tests intuitively.

**Quick Start in 3 Steps!**

1. Clone pynvme from GitHub: https://github.com/pynvme/pynvme
   
.. code-block:: shell

   git clone https://github.com/pynvme/pynvme

2. Build pynvme:

.. code-block:: shell

   cd pynvme
   ./install.sh

3. Run pynvme tests. 

.. code-block:: shell

   make setup
   make test TESTS="driver_test.py::test_ioworker_iops_multiple_queue[1]"

In this document, we explain the design and usage of pynvme, and you can soon build your own tests of NVMe devices.


.. image:: slogen.png
   :target: slogen.png
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
