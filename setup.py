from setuptools import setup, find_packages


def open_requirements(fname):
    with open(fname, mode='r') as f:
        requires = f.read().split('\n')
    requires = [e for e in requires if len(e) > 0 and not e.startswith('#')]
    return requires

install_requires = open_requirements('requirements.txt')


d = {}
exec(open("spikeinterface_gui/version.py").read(), None, d)
version = d['version']
long_description = open("README.md").read()

pkg_name = "spikeinterface-gui"

setup(
    name=pkg_name,
    version=version,
    author="Samuel Garcia",
    author_email="sam.garcia.die@gmail.com",
    description="GUI for spikeinterface objects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SpikeInterface/spikeinterface-gui",
    packages=find_packages(),
    include_package_data=True,
    package_data={},
    install_requires=install_requires,
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    entry_points={
          'console_scripts': ['sigui=spikeinterface_gui.main:run_mainwindow_cli'],
        },    
)
