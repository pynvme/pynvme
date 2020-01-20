# for pypi package information

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pynvme",
    version="1.7",
    author="Crane Chu",
    author_email="cranechu@gmail.com",
    description="test NVMe devices in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pynvme/pynvme",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: C",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.5',
)
