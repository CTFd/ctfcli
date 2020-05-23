# -*- coding: utf-8 -*-
import re

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

import os

with open("ctfcli/__init__.py") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)


def read(fname):
    try:
        with open(os.path.join(os.path.dirname(__file__), fname), "r") as fp:
            return fp.read().strip()
    except IOError:
        return ""


setup(
    name="ctfcli",
    version=version,
    author="Kevin Chung",
    author_email="kchung@ctfd.io",
    license="Apache 2.0",
    description="Tool for creating and running Capture The Flag competitions",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    keywords=["ctf"],
    classifiers=[],
    install_requires=[
        "cookiecutter==1.6.0",
        "click==7.0",
        "fire==0.2.1",
        "pyyaml==5.2",
        "Pygments==2.5.2",
        "requests==2.22.0",
        "colorama==0.4.3",
        "appdirs==1.4.3",
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={"console_scripts": ["ctf = ctfcli.__main__:main"]},
)
