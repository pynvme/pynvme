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


#find the first NVMe device as the DUT
pciaddr := $(shell lspci -D | grep 'Non-Volatile memory' | grep -o '....:..:..\..' | tail -1)

#reserve memory for driver
memsize := 2430   # minimal RAM: 4GB. 2.5GB for pynvme, 1.5GB for system

#pytest test targets
TESTS := driver_test.py

.PHONY: all spdk doc

all: clean
	cd src; make
	mv src/nvme.*.so nvme.so

clean:
	cd src; make clean
	- sudo rm -rf  __pycache__ .pytest_cache cov_report .coverage.* a.out nvme.so nvme.*.so dist pynvme.egg-info build *.log
	- sudo sh -c 'find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf'

spdk:
	cd spdk; make clean; ./configure --enable-debug --enable-log-bt --enable-werror --disable-tests --without-ocf --without-vhost --without-virtio --without-pmdk --without-vpp --without-rbd --without-isal; make -j8; cd ..

doc:
	pydocmd simple nvme++ > api.md
	m2r api.md
	mv api.rst doc
	rm api.md
	cd doc; make clean; make html

reset:
	- sudo rm -rf /run/dpdk
	- sudo rm -rf /var/run/dpdk
	sudo ./src/setup.sh cleanup
	sudo ./src/setup.sh reset
	- sudo rm -f /var/tmp/spdk.sock*
	- sudo rm -f /var/tmp/pynvme.sock*
	- sudo rm -rf .pytest_cache
	- sudo fuser -k 4420/tcp
	- sudo sh -c 'find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf'

info:
	- sudo ./src/setup.sh status
	- sudo cat /proc/meminfo
	- sudo cat /proc/cpuinfo
	- sudo cat /etc/*release
	- sudo lspci -s ${pciaddr} -vv
	- ip addr
	- df
	- whoami
	- groups
	- lspci
	- date
	- pwd
	- git status -sb
	- git --no-pager log -1

setup: reset
	- xhost +local:		# enable GUI with root/sudo
	- sudo chmod 777 /tmp
	- sudo sh -c 'find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf'
	- sed -i 's/XXXX:BB:DD.F/${pciaddr}/g' .vscode/settings.json
	sudo HUGEMEM=${memsize} DRIVER_OVERRIDE=uio_pci_generic ./src/setup.sh  	# UIO is recommended

pypi:
	python3 setup.py sdist
	python3 -m twine upload dist/*

tags:
	ctags -e --c-kinds=+l -R --exclude=.git --exclude=ioat --exclude=snippets --exclude=env --exclude=doc

pytest: info
	sudo python3 -B -m pytest $(TESTS) --pciaddr=${pciaddr} -s -v -r Efsx

test:
	- rm test_${pciaddr}.log
	make pytest 2>test_${pciaddr}.log | tee -a test_${pciaddr}.log
	- sudo rm -rf .pytest_cache


# local nvme tcp target
####################################

nvmt: target backend
	sudo ./spdk/scripts/rpc.py nvmf_create_transport -t TCP -p 64
	sudo ./spdk/scripts/rpc.py nvmf_create_subsystem nqn.2016-06.io.spdk:cnode1 -a -s SPDK_NVME_OVER_TCP
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_ns nqn.2016-06.io.spdk:cnode1 lvs/lv1
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_ns nqn.2016-06.io.spdk:cnode1 lvs/lv2
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_ns nqn.2016-06.io.spdk:cnode1 lvs/lv3
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_ns nqn.2016-06.io.spdk:cnode1 lvs/lv4
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_listener nqn.2016-06.io.spdk:cnode1 -t tcp -a 127.0.0.1 -s 4420

target:
	cd ./spdk/app/nvmf_tgt; make
	sudo ./spdk/app/nvmf_tgt/nvmf_tgt --no-pci -m 0xf &
	sleep 3

backend:
# 4 sata drive
	sudo dd if=/dev/zero of=/aio/sda bs=1MB count=1024
	sudo ./spdk/scripts/rpc.py bdev_aio_create /aio/sda AIO0 512
	sudo ./spdk/scripts/rpc.py bdev_aio_create /aio/sdb AIO1 512
	sudo ./spdk/scripts/rpc.py bdev_aio_create /aio/sdc AIO2 512
	sudo ./spdk/scripts/rpc.py bdev_aio_create /aio/sdd AIO3 512 #128G

# 20 splitted vbdev
	sudo ./spdk/scripts/rpc.py bdev_split_create AIO0 6
	sudo ./spdk/scripts/rpc.py bdev_split_create AIO1 6
	sudo ./spdk/scripts/rpc.py bdev_split_create AIO2 6
	sudo ./spdk/scripts/rpc.py bdev_split_create AIO3 2

# raid: fast drive
	sudo ./spdk/scripts/rpc.py bdev_raid_create -n FastDisk -z 64 -r 0 -b "AIO0p0 AIO1p0 AIO2p0 AIO3p0"

# raid: large drive
	sudo ./spdk/scripts/rpc.py bdev_raid_create -n LargeDisk -z 64 -r 0 -b "AIO0p1 AIO1p1 AIO2p1 AIO3p1 AIO0p2 AIO1p2 AIO2p2 AIO0p3 AIO1p3 AIO2p3 AIO0p4 AIO1p4 AIO2p4 AIO0p5 AIO1p5 AIO2p5"

# cache: fast on large, write back
	sudo ./spdk/scripts/rpc.py bdev_ocf_create DISK wb FastDisk LargeDisk

# ram disk
	sudo ./spdk/scripts/rpc.py bdev_malloc_create -b RAM 256 512

# cache: ram on drive, write through
	sudo ./spdk/scripts/rpc.py bdev_ocf_create TOP wt RAM DISK

# lvol: 800GB x4, thin provision
	sudo ./spdk/scripts/rpc.py bdev_lvol_create_lvstore -c 65536 --clear-method write_zeroes TOP lvs
	sudo ./spdk/scripts/rpc.py bdev_lvol_create -l lvs -t --clear-method write_zeroes lv1 819200
	sudo ./spdk/scripts/rpc.py bdev_lvol_create -l lvs -t --clear-method write_zeroes lv2 819200
	sudo ./spdk/scripts/rpc.py bdev_lvol_create -l lvs -t --clear-method write_zeroes lv3 819200
	sudo ./spdk/scripts/rpc.py bdev_lvol_create -l lvs -t --clear-method write_zeroes lv4 819200
