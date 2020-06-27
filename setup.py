# for pypi package information

import os
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


def get_all_subdirs(node):
    exclude_prefixes = ('__', '.')  # exclusion prefixes
    for dirpath, dirnames, filenames in os.walk(node):
        # exclude all dirs starting with exclude_prefixes
        dirnames[:] = [dirname
                       for dirname in dirnames
                       if not dirname.startswith(exclude_prefixes)]
        yield dirpath, dirnames, filenames

def get_test_files(node):
    for pathname, _, filenames in get_all_subdirs(node):
        if filenames:
            yield pathname, [os.path.join(pathname, f) for f in filenames]

test_files = []
for root, filelist in get_test_files("scripts/conformance"):
    test_files.append((root, filelist))


setuptools.setup(
    name="pynvme",
    version="1.9",
    author="Crane Chu",
    author_email="cranechu@gmail.com",
    description="build your own tests.",
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
    install_requires=['pytest', 'pytemperature', 'pylspci', 'quarchpy'],
    data_files=[
        ('pynvme',
         ['nvme.so',
          'identify_nvme',
          'Makefile',
          'conftest.py',
          'driver_test.py',
          'pytest.ini']),
        ('pynvme/src',
         ['src/common.sh',
          'src/setup.sh']),
        ('pynvme/scripts',
         ['scripts/psd.py',
          'scripts/test_examples.py',
          'scripts/test_utilities.py']),
        ('pynvme/scripts/stress',
         ['scripts/stress/dirty_power_cycle_test.py']),
        ('pynvme/include/spdk',
         ['include/spdk/pci_ids.h'])
    ] + test_files,
)
