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


import time
import pytest
import random
import logging
import inspect

import nvme as d


def pytest_addoption(parser):
    parser.addoption(
        "--pciaddr", action="store", default="", help="pci (BDF) address of the device under test, e.g.: 02:00.0"
    )


@pytest.fixture(scope="function", autouse=True)
def script(request):
    # skip empty tests
    sourcecode = inspect.getsourcelines(request.function)[0]
    if 'pass' in sourcecode[-1] and len(sourcecode) < 5:
        pytest.skip("empty test function")

    # measure test time, and set random seed by time
    start_time = time.time()
    d.srand(int(start_time*1000000)&0xffffffff)
    yield
    logging.info("test duration: %.3f sec" % (time.time()-start_time))


@pytest.fixture(scope="session")
def pciaddr(request):
    return request.config.getoption("--pciaddr")


@pytest.fixture(scope="function")
def pcie(pciaddr):
    ret = d.Pcie(pciaddr)
    yield ret
    ret.close()

    
@pytest.fixture(scope="function")
def nvme0(pcie):
    ret = d.Controller(pcie)
    yield ret


@pytest.fixture(scope="function")
def subsystem(nvme0):
    ret = d.Subsystem(nvme0)
    yield ret


@pytest.fixture(scope="function")
def nvme0n1(nvme0):
    ret = d.Namespace(nvme0)
    yield ret
    ret.close()


@pytest.fixture(scope="function")
def qpair(nvme0):
    num_of_entry = (nvme0.cap & 0xffff) + 1
    num_of_entry = min(1024, num_of_entry)
    ret = d.Qpair(nvme0, num_of_entry)
    yield ret
    ret.delete()

    
@pytest.fixture(scope="function")
def tcg(nvme0):
    ret = d.Tcg(nvme0)
    yield ret
    ret.close()


@pytest.fixture(scope="session")
def buf():
    ret = d.Buffer(4096, "pynvme buffer")
    yield ret
    del ret


@pytest.fixture(scope="function")
def verify(nvme0n1):
    ret = nvme0n1.verify_enable(True)
    yield ret


@pytest.fixture(scope="function")
def aer():
    assert False, "aer fixture is replaced by admin command nvme0.aer()"


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()
    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)
