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

#logs directory with timestamp
LOGDIR_BASE := logs
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)
LOGDIR := $(LOGDIR_BASE)/$(TIMESTAMP)
#devices to skip (space-separated PCIe addresses, e.g., "0000:01:00.0 0000:02:00.0")
#mounted devices and OS drive are always skipped automatically
SKIP_DEVICES :=
#pytest test targets
TESTS := driver_test.py

.PHONY: all spdk doc

all: clean
	cd src; make
	mv src/nvme.*.so nvme.so

clean:
	cd src; make clean
	- sudo rm -rf  __pycache__ .pytest_cache cov_report .coverage.* a.out nvme.so nvme.*.so dist pynvme.egg-info build
	- sudo sh -c 'find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf'

clean-logs:
	- sudo rm -rf $(LOGDIR_BASE)

spdk:
	cd spdk; make clean; ./configure --enable-debug --enable-log-bt --enable-werror --disable-tests --without-ocf --without-vhost --without-virtio --without-pmdk --without-vpp --without-rbd --without-isal; make -j8; cd ..

doc: all
	pydocmd simple nvme++ > api.md
	m2r api.md
	mv api.rst doc
	rm api.md
	cd doc; make clean; make html

reset:
	- sudo sh -c "echo 1 > /sys/bus/pci/rescan"
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

pypi: all
	strip -s nvme.so
	python3 setup.py sdist
	python3 -m twine upload dist/*

tags:
	ctags -e --c-kinds=+l -R --exclude=.git --exclude=ioat --exclude=snippets --exclude=env --exclude=doc

pytest: info
	@mkdir -p $(LOGDIR)
	@ln -sfn $(TIMESTAMP) $(LOGDIR_BASE)/latest
	@echo "Logs will be saved to: $(LOGDIR)"
	sudo PYNVME_LOGDIR=$(LOGDIR) python3 -B -m pytest $(TESTS) --pciaddr=${pciaddr} -s -v -r Efsx --excelreport=$(LOGDIR)/report.xls --verbose

test:
	@mkdir -p $(LOGDIR)
	@ln -sfn $(TIMESTAMP) $(LOGDIR_BASE)/latest
	@echo "Logs will be saved to: $(LOGDIR)"
	make pytest LOGDIR=$(LOGDIR) 2>$(LOGDIR)/test_${pciaddr}.log | tee -a $(LOGDIR)/test_${pciaddr}.log
	- sudo rm -rf .pytest_cache

# Run tests on all available (unmounted) NVMe devices
# Usage: make test-all-devices TESTS="scripts/" [SKIP_DEVICES="0000:01:00.0 0000:02:00.0"]
test-all-devices:
	@echo "========================================"
	@echo "Discovering available NVMe devices..."
	@echo "========================================"
	@if [ -n "$(SKIP_DEVICES)" ]; then \
		echo "User-defined skip list: $(SKIP_DEVICES)"; \
	fi
	@echo ""
	@tested=0; skipped=0; \
	for bdf in $$(lspci -D | grep 'Non-Volatile memory' | grep -o '....:..:..\..' ); do \
		echo ""; \
		echo "Checking device: $$bdf"; \
		skip_reason=""; \
		\
		for skip_dev in $(SKIP_DEVICES); do \
			if [ "$$bdf" = "$$skip_dev" ]; then \
				skip_reason="User skip list"; \
				break; \
			fi; \
		done; \
		\
		if [ -z "$$skip_reason" ]; then \
			for nvme in $$(ls /sys/bus/pci/devices/$$bdf/nvme 2>/dev/null); do \
				for ns in $$(ls /sys/bus/pci/devices/$$bdf/nvme/$$nvme 2>/dev/null | grep nvme); do \
					mountpoint=$$(lsblk /dev/$$ns --output MOUNTPOINT -n 2>/dev/null | head -1); \
					if [ -n "$$mountpoint" ]; then \
						if [ "$$mountpoint" = "/" ]; then \
							skip_reason="ROOT/OS drive (/)"; \
						else \
							skip_reason="Mounted at $$mountpoint"; \
						fi; \
						break 2; \
					fi; \
				done; \
			done; \
		fi; \
		\
		if [ -n "$$skip_reason" ]; then \
			echo "  [SKIP] Reason: $$skip_reason"; \
			skipped=$$((skipped + 1)); \
		else \
			echo "  [TEST] Device available for testing"; \
			echo "========================================"; \
			echo "Running tests on: $$bdf"; \
			echo "========================================"; \
			$(MAKE) test TESTS="$(TESTS)" pciaddr="$$bdf" || true; \
			tested=$$((tested + 1)); \
		fi; \
	done; \
	echo ""; \
	echo "========================================"; \
	echo "Summary: $$tested device(s) tested, $$skipped device(s) skipped"; \
	echo "Check logs in: $(LOGDIR_BASE)/"; \
	echo "========================================"

# List all available NVMe devices for testing
# Usage: make list-devices [SKIP_DEVICES="0000:01:00.0"]
list-devices:
	@echo "========================================"
	@echo "NVMe Devices in System"
	@echo "========================================"
	@if [ -n "$(SKIP_DEVICES)" ]; then \
		echo "User-defined skip list: $(SKIP_DEVICES)"; \
		echo ""; \
	fi
	@for bdf in $$(lspci -D | grep 'Non-Volatile memory' | grep -o '....:..:..\..' ); do \
		device_name=$$(lspci -s $$bdf | cut -d: -f3-); \
		echo ""; \
		echo "Device: $$bdf -$$device_name"; \
		status="Available for testing"; \
		\
		for skip_dev in $(SKIP_DEVICES); do \
			if [ "$$bdf" = "$$skip_dev" ]; then \
				status="SKIP (user-defined)"; \
				break; \
			fi; \
		done; \
		\
		for nvme in $$(ls /sys/bus/pci/devices/$$bdf/nvme 2>/dev/null); do \
			for ns in $$(ls /sys/bus/pci/devices/$$bdf/nvme/$$nvme 2>/dev/null | grep nvme); do \
				mountpoint=$$(lsblk /dev/$$ns --output MOUNTPOINT -n 2>/dev/null | head -1); \
				if [ -n "$$mountpoint" ]; then \
					if [ "$$mountpoint" = "/" ]; then \
						echo "  /dev/$$ns mounted at: / [ROOT/OS DRIVE]"; \
						status="PROTECTED (ROOT/OS drive)"; \
					else \
						echo "  /dev/$$ns mounted at: $$mountpoint [MOUNTED]"; \
						status="PROTECTED (mounted)"; \
					fi; \
				else \
					echo "  /dev/$$ns - not mounted"; \
				fi; \
			done; \
		done; \
		echo "  Status: $$status"; \
	done
	@echo ""
	@echo "========================================"
	@echo "Commands:"
	@echo "  make test pciaddr=XXXX:XX:XX.X            - Test specific device"
	@echo "  make test-all-devices TESTS=\"...\"         - Test all available devices"
	@echo "  make test-all-devices SKIP_DEVICES=\"...\"  - Skip specific devices"
	@echo "========================================"


# local nvme tcp target
####################################

nvmt: target backend
	sudo ./spdk/scripts/rpc.py nvmf_create_transport -t TCP -p 64
	sudo ./spdk/scripts/rpc.py nvmf_create_subsystem nqn.2016-06.io.spdk:cnode1 -a -s SPDK_NVME_OVER_TCP
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_ns nqn.2016-06.io.spdk:cnode1 RAMDisk
	sudo ./spdk/scripts/rpc.py nvmf_subsystem_add_listener nqn.2016-06.io.spdk:cnode1 -t tcp -a 127.0.0.1 -s 4420

target:
	cd ./spdk/app/nvmf_tgt; make
	sudo ./spdk/app/nvmf_tgt/nvmf_tgt --no-pci -m 0xf &
	sleep 3

backend:
	sudo ./spdk/scripts/rpc.py bdev_malloc_create -b RAMDisk 256 512
