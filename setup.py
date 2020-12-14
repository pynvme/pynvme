#
#  BSD LICENSE
#
#  Copyright (c) Crane Chu <cranechu@gmail.com>
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#    * Neither the name of Intel Corporation nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-


# for pypi package information
import setuptools
import subprocess
from setuptools.command.install import install

class CustomInstall(install):
    def run(self):
        subprocess.call("sudo dnf install -y make", shell=True)
        install.run(self)

with open("README.md", "r") as fh:
    long_description = fh.read()

    
setuptools.setup(
    name="pynvme",
    version="2.3.1",
    author="Crane Chu",
    author_email="cranechu@gmail.com",
    description="builds your own tests.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pynvme/pynvme",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: C",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.5',
    install_requires=['pytest',
                      'pytest-excel',
                      'libpci',
                      'pylspci',
                      'quarchpy',
                      'pytemperature'],
    data_files=[
        ('pynvme',
         ['nvme.so',
          'Makefile',
          'conftest.py',
          'driver_test.py',
          'pytest.ini']),
        ('pynvme/src',
         ['src/common.sh',
          'src/setup.sh']),
        ('pynvme/scripts',
         ['scripts/psd.py',
          'scripts/tcg.py',
          'scripts/zns.py',
          'scripts/test_examples.py',
          'scripts/test_utilities.py']),
        ('pynvme/scripts/stress',
         ['scripts/stress/dirty_power_cycle_test.py']),
        ('pynvme/include/spdk',
         ['include/spdk/pci_ids.h']),
    ],
    cmdclass={'install': CustomInstall},
)
