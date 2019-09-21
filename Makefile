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


#SPDK infrastructure
SPDK_ROOT_DIR := $(abspath $(CURDIR)/spdk)
include $(SPDK_ROOT_DIR)/mk/spdk.common.mk

C_SRCS = driver.c
LIBNAME = pynvme

include $(SPDK_ROOT_DIR)/mk/spdk.lib.mk

#find the first NVMe device as the DUT
pciaddr=$(shell lspci | grep 'Non-Volatile memory' | grep -o '..:..\..' | head -1)

#reserve memory for driver
memsize=$(shell free -m | awk 'NR==2{print ($$2-$$2%4)/2}')

#pytest test targets
TESTS := driver_test.py

#cython part
clean: cython_clean
cython_clean:
	@sudo rm -rf build *.o nvme.*.so cdriver.c driver_wrap.c __pycache__ .pytest_cache cov_report .coverage.* scripts/__pycache__

all: cython_lib
.PHONY: all spdk doc

spdk:
	cd spdk; make clean; ./configure --enable-debug --disable-tests --without-vhost --without-virtio --without-isal; make; cd ..

doc: cython_lib
	pydocmd simple nvme++ > api.md
	sed -i "1s/.*/# API/" api.md
	m2r	api.md
	mv api.rst doc
	rm api.md
	cd doc; make clean; make html

reset:
	sudo ./spdk/scripts/setup.sh cleanup
	sudo ./spdk/scripts/setup.sh reset
	-sudo rm -f /var/tmp/pynvme.sock*
	-sudo rm -rf .pytest_cache
	-sudo fuser -k 4420/tcp

info:
	- sudo ./spdk/scripts/setup.sh status
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
	-xhost +local:		# enable GUI with root/sudo
	-sudo chmod 777 /tmp
	-ulimit -n 2048
	sudo HUGEMEM=${memsize} DRIVER_OVERRIDE=uio_pci_generic ./spdk/scripts/setup.sh  	# use UIO only

cython_lib:
	@python3 setup.py build_ext -i --force

tags:
	ctags -e --c-kinds=+l -R --exclude=.git --exclude=test --exclude=ioat --exclude=bdev --exclude=snippets --exclude=env

pytest: info
	sudo python3 -B -m pytest $(TESTS) --pciaddr=${pciaddr} -s -x -v -r Efsx

test:
	-rm test.log
	make pytest 2>test.log | tee -a test.log

nvmt:
	cd ./spdk/app/nvmf_tgt; make
	sudo ./spdk/app/nvmf_tgt/nvmf_tgt --no-pci -m 0x3 &
	sleep 5
	sudo ./spdk/scripts/rpc.py construct_malloc_bdev -b Malloc0 1024 512
	sudo ./spdk/scripts/rpc.py nvmf_create_transport -t TCP -p 10
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_create nqn.2016-06.io.spdk:cnode1 -a -s SPDK00000000000001
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_ns nqn.2016-06.io.spdk:cnode1 Malloc0
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_listener nqn.2016-06.io.spdk:cnode1 -t tcp -a 127.0.0.1 -s 4420
