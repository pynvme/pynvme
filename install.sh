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

#!/usr/bin/env bash


if [ -s /etc/redhat-release ]; then
    # fedora, centos7
    sudo yum install -y make redhat-rpm-config python3-devel python3-pip python3-tkinter
elif [ -f /etc/debian_version ]; then
    # ubuntu
    sudo apt install -y python3-setuptools python3-dev python3-pip python3-tk
elif [ -f /etc/SUSE-brand ]; then
    # SUSE
    sudo zypper install -y python3-setuptools python3-devel python3-pip python3-tk
elif [ -f /etc/arch-release ]; then
    # ArchLinux
    sudo pacman -S python3-setuptools python3-devel python3-pip tk
else
    echo "unknown system type."
    exit 1
fi

# get depended source code and software
git submodule update --init spdk
cd spdk && git submodule update --init dpdk && cd ..
sudo ./spdk/scripts/pkgdep.sh
sudo python3 -m pip install --upgrade pip
sudo python3 -m pip install -r requirements.txt

# checkout and config pynvme code in SPDK and DPDK
cd spdk && git checkout pynvme_2.3
cd dpdk && git checkout pynvme_2.0 && cd ..
./configure --without-isal && cd ..

# compile
make spdk                                    # compile SPDK
make                                         # compile pynvme

# quick test after compile
make setup
make test TESTS=scripts/test_examples.py::test_hello_world

echo "pynvme install done."
