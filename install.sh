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

git submodule update --init --recursive
cd spdk; ./configure --without-isal; cd ..   # configurate SPDK
make spdk                                    # compile SPDK
make clean; make
