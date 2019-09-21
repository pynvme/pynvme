pynvme
======

The pynvme is a python extension module. Users can operate NVMe SSD intuitively in Python scripts. It is designed for NVMe SSD testing with performance considered. Integrated with third-party tools, vscode and pytest, pynvme provides a convenient and professional solution to test NVMe devices.

The pynvme wraps SPDK NVMe driver in a Python extension, with abstracted classes, e.g. Controller, Namespace, Qpair, Buffer, and IOWorker. With pynvme, users can operate NVMe devices intuitively, including:


#. access PCI configuration space
#. access NVMe registers in BAR space
#. send any NVMe admin/IO commands
#. callback functions are supported
#. MSIx interrupt is supported
#. transparent checksum verification for each LBA
#. IOWorker generates high-performance IO
#. integrated with pytest
#. integrated with VSCode
#. test multiple controllers, namespaces and qpairs simultaneously
#. test NVMe over TCP targets

Before moving forward, check and backup your data in the NVMe SSD to be tested. It is always recommended to attach just one piece of NVMe SSD in your system to avoid mistakes.

.. toctree::
   :maxdepth: 2
   :hidden:
          
   install
   vscode
   tutorial
   features
   pytest
   api
   development

We made a speech on SPDK Summit 2019 in Beijing. Here is the :download:`presentation file <_static/02_Presentation_26_Why_SSD_Developers_Need_Pynvme_and_Why_Pynvme_Needs_SPDK_Crane.pdf>`.
