#!/usr/bin/env bash

if [ -s /etc/redhat-release ]; then
  # fedora
  sudo dnf update -y
  sudo dnf install -y make redhat-rpm-config python3-devel python3-pip 
elif [ -f /etc/debian_version ]; then
  # ubuntu
  sudo apt-get install -y python3-pip
else
  echo "unknown system type."
  exit 1
fi

# get depended source code and software
git submodule update --init --recursive
sudo ./spdk/scripts/pkgdep.sh
sudo pip3 install -r requirements.txt

# config SPDK for first time
cd spdk; git checkout pynvme; ./configure --without-isal; cd ..

# compile
make spdk                                    # compile SPDK
make                                         # compile pynvme

