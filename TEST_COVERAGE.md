# pynvme Test Coverage Reference

This document provides a comprehensive breakdown of all **78 test cases** in the pynvme framework, organized by test suite and coverage area.

---

## Quick Start Guide

### System Requirements

| Requirement | Details |
|-------------|---------|
| **OS** | Linux (Fedora recommended) |
| **CPU** | Intel x86_64, 4+ cores |
| **RAM** | 4GB minimum (2.5GB for pynvme + 1.5GB for system) |
| **Storage** | NVMe SSD for testing (data will be destroyed!) |
| **Python** | Python 3.x (Python 2 not supported) |
| **Privileges** | sudo/root access required |

### BIOS Settings (Must Disable)

- IOMMU (VT-d)
- Secure Boot
- Intel RST (RAID mode)
- VMD

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/pynvme/pynvme
cd pynvme

# 2. Install everything (SPDK + pynvme + dependencies)
./install.sh

# 3. Or install manually:
# Install system packages (Fedora)
sudo dnf install -y make redhat-rpm-config python3-devel python3-pip

# Install system packages (Ubuntu)
sudo apt install -y python3-setuptools python3-dev python3-pip

# Get SPDK submodules
git submodule update --init --recursive

# Install SPDK dependencies
sudo ./spdk/scripts/pkgdep.sh

# Install Python packages
sudo python3 -m pip install -r requirements.txt

# Build SPDK
make spdk

# Build pynvme
make
```

### Python Dependencies

```bash
# Install from requirements.txt
sudo pip3 install -r requirements.txt

# Key packages:
# - pytest          : Test framework
# - pytest-excel    : Excel report generation  
# - matplotlib      : Performance graphs
# - openpyxl        : Excel file handling
# - pytemperature   : Temperature conversion
# - quarchpy        : (Optional) Quarch power control hardware
```

---

## Running Tests

### Step 1: Setup SPDK Runtime Environment

```bash
# This allocates hugepages and unbinds NVMe from kernel driver
# WARNING: Your test NVMe SSD will be unavailable to the OS after this!
make setup
```

### Step 2: Run Tests

#### Run Complete Test Suite

```bash
# Run ALL tests
make test TESTS="scripts/"

# Run all tests with specific device
make test TESTS="scripts/" pciaddr="0000:01:00.0"
```

#### Run One Test Suite (Directory or File)

```bash
# Run Examples suite
make test TESTS="scripts/test_examples.py"

# Run Performance suite (all files in directory)
make test TESTS="scripts/performance/"

# Run Stress suite
make test TESTS="scripts/stress/"

# Run FTL suite
make test TESTS="scripts/ftl/"

# Run PSD (Protocol) tests
make test TESTS="scripts/psd.py"
```

#### Run One Test Case

```bash
# Run a single test by name
make test TESTS="scripts/test_examples.py::test_hello_world"

# Run a specific parameterized test
make test TESTS="scripts/test_examples.py::test_ioworker_iops_multiple_queue[4]"

# Run tests matching a keyword
make pytest TESTS="scripts/ -k ioworker"
```

#### Using pytest Directly

```bash
# Basic usage
sudo python3 -B -m pytest scripts/test_examples.py --pciaddr=0000:01:00.0 -v

# Run with keyword filter
sudo python3 -B -m pytest scripts/ -k "trim" --pciaddr=0000:01:00.0 -v

# Run and generate JUnit XML report
sudo python3 -B -m pytest scripts/ --pciaddr=0000:01:00.0 --junitxml=results.xml
```

#### Multi-Device Testing

When your system has multiple NVMe drives, you can test them all automatically.

**Protection Layers (Automatic):**

| Layer | Protection | Description |
|-------|------------|-------------|
| 1 | ROOT/OS drive | Drives mounted at `/` are always skipped |
| 2 | Mounted drives | Any drive with active mountpoints is skipped |
| 3 | User skip list | Optionally skip additional devices |

**List All Devices:**

```bash
# Show all NVMe devices and their status
make list-devices

# Check with custom skip list
make list-devices SKIP_DEVICES="0000:04:00.0"
```

**Test All Available Devices:**

```bash
# Run tests on ALL unmounted NVMe devices
make test-all-devices TESTS="scripts/test_examples.py"

# Run full suite on all devices
make test-all-devices TESTS="scripts/"

# Skip specific devices (in addition to mounted ones)
make test-all-devices TESTS="scripts/" SKIP_DEVICES="0000:04:00.0"

# Skip multiple devices
make test-all-devices TESTS="scripts/" SKIP_DEVICES="0000:03:00.0 0000:04:00.0"
```

**Example Output:**

```
========================================
Discovering available NVMe devices...
========================================

Checking device: 0000:01:00.0
  [SKIP] Reason: ROOT/OS drive (/)

Checking device: 0000:02:00.0
  [SKIP] Reason: Mounted at /data

Checking device: 0000:03:00.0
  [TEST] Device available for testing
========================================
Running tests on: 0000:03:00.0
========================================
...

========================================
Summary: 1 device(s) tested, 2 device(s) skipped
========================================
```

### Step 3: Check Results

```bash
# View latest test log
cat logs/latest/test_*.log

# View test summary (end of log)
tail -50 logs/latest/test_*.log

# Open Excel report
ls logs/latest/report.xls
```

### Step 4: Cleanup (Return NVMe to Kernel)

```bash
# Release NVMe device back to kernel control
make reset
```

---

## Log Files

All logs are saved to timestamped directories:

```
logs/
├── latest -> 20260601_143052/     # Symlink to most recent run
├── 20260601_143052/               # Test run 1
│   ├── test_0000:01:00.0.log      # Full console output
│   ├── report.xls                 # Excel test report
│   ├── report.csv                 # Performance data
│   ├── performance_report.xlsx    # Performance summary
│   ├── lat_hist_*.png             # Latency histograms
│   └── iops.png                   # IOPS graph
└── 20260601_162045/               # Test run 2
    └── ...
```

### Clean Logs

```bash
# Remove all log directories
make clean-logs
```

---

## Test Execution Summary

At the end of each test run, you'll see:

```
==================== short test summary info ====================
PASSED scripts/test_examples.py::test_hello_world
PASSED scripts/test_examples.py::test_buffer_read_write
SKIPPED scripts/stress/dirty_power_cycle_test.py::test_quarch_dirty_power_cycle_single
FAILED scripts/stress/marathon_test.py::test_ioworker_longtime

=============== 45 passed, 2 skipped, 1 failed in 125.34s ===============
```

---

## Common Commands Reference

| Command | Description |
|---------|-------------|
| `make setup` | Setup SPDK, allocate hugepages, bind NVMe |
| `make reset` | Release NVMe back to kernel |
| `make test TESTS="..."` | Run tests on single device |
| `make test pciaddr="..."` | Run tests on specific device |
| `make list-devices` | List all NVMe devices with status |
| `make test-all-devices TESTS="..."` | Run tests on all available devices |
| `make test-all-devices SKIP_DEVICES="..."` | Skip specific devices |
| `make clean-logs` | Delete all log directories |
| `make info` | Show system and device info |

---

## Overview

| Suite | Test Files | Test Count |
|-------|------------|------------|
| **Examples** | `scripts/test_examples.py` | 28 |
| **PSD (Protocol Spec/Driver)** | `scripts/psd.py` | 16 |
| **Performance** | `scripts/performance/` | 15 |
| **Stress** | `scripts/stress/` | 10 |
| **FTL** | `scripts/ftl/` | 3 |
| **ZNS** | `scripts/zns.py` | 1 |
| **Trace** | `scripts/trace/test_replayer.py` | 1 |
| **Total** | | **78** |

> **Note:** 2 tests require the `quarchpy` module (dirty power cycle tests). The remaining 76 tests can run without it.

---

## Examples Suite (`scripts/test_examples.py`) - 28 tests

| Test Case | Coverage Area |
|-----------|--------------|
| `test_hello_world` | Basic read/write operations, qpair handling, command callbacks |
| `test_registers_and_identify_data` | PCIe/NVMe register access, identify data parsing |
| `test_sanitize` | Sanitize command, log page polling |
| `test_ioworker_simplified` | IOWorker basic usage with variable IO sizes |
| `test_ioworker_with_temperature_and_trim` | Multiprocessing, trim commands, SMART temperature log |
| `test_multiple_controllers_and_namespaces` | Multi-controller/namespace support, throughput measurement |
| `test_power_and_reset` | ASPM, PCI PM states, controller/PCIe/subsystem resets |
| `test_different_io_size_and_count` | Parameterized IO size/count testing |
| `test_fused_operations` | Fused compare-and-write commands |
| `test_send_cmd_2sq_1cq` | Protocol-level queue management (2 SQ sharing 1 CQ) |
| `test_sanitize_operations_basic` | Sanitize with AER notification |
| `test_buffer_read_write` | DMA buffer operations, physical address access |
| `test_create_qpairs` | Queue pair creation limits |
| `test_namespace_multiple` | Write uncorrectable, multiple namespace handling |
| `test_ioworker_iops_multiple_queue` | Multi-queue IOPS measurement |
| `test_ioworker_fixed_iops` | Rate-limited IOWorker |
| `test_dsm_trim` | DSM trim command (single/multiple ranges) |
| `test_ioworker_performance` | Performance metrics with percentile latency |
| `test_ioworker_jedec_enterprise_workload` | JEDEC enterprise workload pattern |
| `test_power_on_off` | Custom power callbacks |
| `test_init_nvme_customerized` | Custom NVMe initialization sequence |
| `test_ioworker_op_dict_trim` | IOWorker with operation distribution |
| `test_ioworker_io_sequence_read_write_trim_flush_uncorr` | IO sequence replay |
| `test_aer_with_multiple_sanitize` | Multiple sanitize with AER |
| `test_verify_partial_namespace` | Partial namespace verification |
| `test_jsonrpc_list_qpairs` | JSON-RPC interface for queue management |
| `test_powercycle_with_qpair` | Power cycle with active queue pairs |
| `test_reset_time` | Reset timing measurement |
| `test_power_state_transition` | Power state transitions with IO verification |
| `test_getlogpage_nsid` | Log page with namespace ID |
| `test_ioworker_with_temperature` | Multi-IOWorker with temperature monitoring |
| `test_ioworker_jedec_enterprise_workload_512` | JEDEC enterprise 512B sector |

---

## PSD (Protocol Spec/Driver) Suite (`scripts/psd.py`) - 16 tests

| Test Case | Coverage Area |
|-----------|--------------|
| `test_create_delete_iocq` | IO Completion Queue create/delete, error handling |
| `test_create_delete_iocq_large` | Large CQ sizes (1-1024 pages) |
| `test_create_delete_iocq_non_contig` | Non-contiguous CQ memory |
| `test_create_delete_iosq` | IO Submission Queue create/delete, error paths |
| `test_send_single_cmd` | Single command submission, invalid namespace |
| `test_prp_and_prp_list` | PRP/PRP list buffer handling (1-512 entries) |
| `test_prp_and_prp_list_with_offset` | PRP with memory offsets |
| `test_prp_and_prp_list_invalid` | Invalid PRP index boundary |
| `test_send_cmd_different_qdepth` | Variable queue depths (2-31) |
| `test_send_cmd_2sq_1cq` | Protocol-level 2 SQ sharing 1 CQ |
| `test_psd_write_2sq_1cq_prp_list` | Multi-SQ write with PRP list |
| `test_iocq_prplist` | PRP list buffer offset calculations |
| `test_psd_with_qpair` | PSD queue vs SPDK qpair coexistence |
| `test_write_before_power_cycle` | Burst write before sudden power loss |
| `test_invalid_sq_doorbell` | Invalid doorbell handling, AER |
| `test_write_read_verify` | Write-read-verify sequence |

---

## Performance Suite (`scripts/performance/`) - 15 tests

### 1_fresh_perf_test.py (6 tests)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_create_report_file` | Report setup, drive info collection |
| `test_empty_read_performance` | Empty drive read performance |
| `test_1gb_read_write_performance` | 1GB region seq/rand R/W |
| `test_fill_drive_first_pass` | Full drive sequential write |
| `test_fill_drive_random` | Full drive random write |
| `test_fill_drive_after_random` | Sequential write after random (×2 repeats) |

### 2_init_time_test.py (2 tests, parameterized)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_boot_time_rand` | Boot time after random write (×10 repeats × clean/dirty) |
| `test_boot_time_seq` | Boot time after sequential write (×10 repeats × clean/dirty) |

### 3_steady_perf_test.py (3 tests)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_clean_and_fill_drive` | Clean + fill for steady state |
| `test_random_write_small_region` | 20% region random write |
| `test_steady_iops_latency` | Steady state IOPS/latency (×7 read percentages) |

### 4_nvme_cmd_test.py (3 tests, parameterized)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_trim_time_one_range` | Single-range trim time (×3 sizes × 10 repeats) |
| `test_trim_time_all_range_buffer` | Full-buffer trim time (×5 sizes × 10 repeats) |
| `test_format_time` | Format command time (×10 repeats) |

### 5_generate_report_test.py (1 test)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_generate_report_xlsx` | Excel report generation from CSV data |

---

## Stress Suite (`scripts/stress/`) - 10 tests

### dirty_power_cycle_test.py (3 tests)

| Test Case | Coverage Area | Requires Quarch |
|-----------|--------------|-----------------|
| `test_precondition_format` | Pre-test formatting/reset | No |
| `test_quarch_dirty_power_cycle_single` | Dirty power cycle with data verification | **Yes** |
| `test_quarch_dirty_power_cycle_multiple` | Repeated dirty power cycles (×10) | **Yes** |

### endurance_test.py (3 tests)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_ioworker_jedec_enterprise_workload_512` | 12-hour JEDEC enterprise workload (512B) |
| `test_ioworker_jedec_enterprise_workload_4k` | 12-hour JEDEC enterprise workload (4KB) |
| `test_replay_jedec_client_trace` | JEDEC client trace file replay |

### reset_with_io_test.py (2 tests)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_precondition_format` | Pre-test formatting |
| `test_reset_within_ioworker` | Reset during active IO (×10 repeats) |

### marathon_test.py (2 tests)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_ioworker_longtime` | Long-running multi-queue IO |
| `test_write_and_read_to_eol` | Write/read cycles to end-of-life |

---

## FTL Suite (`scripts/ftl/`) - 3 tests

### trim_test.py (1 test)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_trim_basic` | Trim command with data verification, bandwidth measurement |

### swl_test.py (2 tests)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_swl_only` | Static wear leveling (sequential hot data) |
| `test_swl_with_gc` | Static wear leveling with garbage collection |

---

## Other Tests - 2 tests

### zns.py (1 test)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_zns_write` | Zoned Namespace (ZNS) write operations |

### trace/test_replayer.py (1 test)

| Test Case | Coverage Area |
|-----------|--------------|
| `test_replay_pynvme_trace` | IO trace file replay with latency histogram |

---

## Test Coverage Summary by Category

| Category | Count | Coverage Areas |
|----------|-------|----------------|
| **Basic IO/Commands** | ~25 | Read, write, flush, trim, compare, fused ops |
| **Queue Management** | ~12 | CQ/SQ create/delete, depths, PRP/PRP lists |
| **Power/Reset** | ~10 | Power states, ASPM, controller/PCIe/subsystem resets |
| **Performance** | ~15 | IOPS, latency, throughput, boot time |
| **Stress/Endurance** | ~10 | Long-duration, power cycles, data integrity |
| **Protocol/Spec** | ~6 | Doorbells, error handling, AER |

---

## Running Tests

```bash
# Run all tests
pytest scripts/

# Run specific suite
pytest scripts/test_examples.py
pytest scripts/performance/
pytest scripts/stress/

# Run single test
pytest scripts/test_examples.py::test_hello_world

# Exclude quarch-dependent tests
pytest scripts/ --ignore=scripts/stress/dirty_power_cycle_test.py
```

---

*Generated: June 2026*
