VSCode
======

The pynvme works with VSCode! And pytest too!


#. 
   First of all, install vscode here: https://code.visualstudio.com/

#. 
   Root user is not recommended in vscode, so just use your ordinary non-root user. It is required to configurate the user account to run sudo without a password.

   .. code-block:: shell

      sudo visudo

#. 
   In order to monitor qpairs status and cmdlog along the progress of testing, user can install vscode extension pynvme-console. The extension provides DUT status and cmdlogs in VSCode UI.

   .. code-block:: shell

      code --install-extension pynvme-console-1.x.x.vsix

#. 
   Before start vscode, modify .vscode/settings.json with the correct pcie address (bus:device.function, which can be found by lspci shell command) of your DUT device.

   .. code-block:: shell

      lspci
      # 01:00.0 Non-Volatile memory controller: Lite-On Technology Corporation Device 2300 (rev 01)

#. 
   Then in pynvme folder, we can start vscode to edit, debug and run scripts:

   .. code-block:: shell

      make setup; code .  # make sure to enable SPDK nvme driver before starting vscode

#. 
   Users can add their own script files under scripts directory. Import following packages in new test script files.

   .. code-block:: python

      import pytest
      import logging
      import nvme as d    # import pynvme's python package


   7. Now, we can debug and run test scripts in VSCode!

.. image:: pic/vscode_area.png
   :target: pic/vscode_area.png
   :alt: vscode screenshot
      
A. Activity Bar: you can select the last Test icon for pytest and pynvme extentions.
B. pytest panel: collects all test files and cases in scripts directory.
C. pynvme panel: displays all active qpairs in all controllers. Click qpair to open or refresh its cmdlog viewer.
D. editor: edit test scripts here.
E. cmdlog viewer: displays the latest 128 command and completion dwords in one qpair.
F. log viewer: displays pytest log.

   VSCode is convenient and powerful, but it consumes a lot of resources. So, for formal performance tests and regular CI tests, it is recommended to run tests in command line, by *make test*.
