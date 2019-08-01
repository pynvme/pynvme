import time
import yaml
import pytest
import logging
import inspect

import nvme as d


def pytest_addoption(parser):
    parser.addoption(
        "--pciaddr", action="store", default="", help="pci (BDF) address of the device under test, e.g.: 02:00.0"
    )


@pytest.fixture(scope="session")
def pciaddr(request):
    ret = request.config.getoption("--pciaddr")
    logging.info("running tests on DUT %s" % ret)
    return ret


@pytest.fixture(scope="function", autouse=True)
def script(request):
    # skip empty tests
    sourcecode = inspect.getsourcelines(request.function)[0]
    if 'pass' in sourcecode[-1] and len(sourcecode) < 5:
        pytest.skip("empty test function")

    # measure test time
    start_time = time.time()
    yield
    logging.info("test duration: %.3f sec" % (time.time()-start_time))


@pytest.fixture(scope="session")
def nvme0(pciaddr):
    ret = d.Controller(pciaddr.encode('utf-8'))
    yield ret
    del ret


@pytest.fixture(scope="session")
def subsystem(nvme0):
    ret = d.Subsystem(nvme0)
    yield ret
    del ret


@pytest.fixture(scope="session")
def pcie(nvme0):
    ret = d.Pcie(nvme0)
    yield ret
    del ret


@pytest.fixture(scope="function")
def nvme0n1(nvme0):
    ret = d.Namespace(nvme0, 1)
    yield ret
    ret.close()
    del ret

    
@pytest.fixture(scope="session")
def buf():
    ret = d.Buffer(40967, "default buffer")
    yield ret
    del ret


@pytest.fixture(scope="function")
def aer(nvme0):
    def register_cb(func):
        logging.debug("register aer callback function: %s" % func.__name__)
        nvme0.register_aer_cb(func)
    yield register_cb
    logging.debug("unregister aer callback function")
    nvme0.register_aer_cb(None)


@pytest.fixture(scope="function")
def verify():
    a = d.config(verify=False)
    b = d.config(verify=True)
    yield a!=b  # return True if config success
    d.config(verify=False)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()
    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)
