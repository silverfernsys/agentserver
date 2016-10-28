# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

import agentserver

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='agentserver',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=agentserver.__version__,

    description='A server for managing monitoring agents',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/silverfernsys/agentserver',

    # Author details
    author='Silver Fern Systems',
    author_email='dev@silverfern.io',

    # Choose your license
    license='BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: BSD License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
    ],

    # What does your project relate to?
    keywords='monitoring development',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'Cerberus==0.9.2',
        'configutil',
        'iso8601utils',
        'passlib',
        'pyfiglet',
        'setproctitle',
        'sqlalchemy',
        'tabulate',
        'termcolor',
        'tornado',
    ],

    dependency_links=['https://github.com/silverfernsys/pydruid.git=pydruid-0.4.0beta'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'postgres': ['psycopg2'],
        'mysql': ['PyMySQL'],
        'druid': ['pydruid', 'kafka-python'],
        'test': ['coverage', 'codecov', 'pytest', 'mock'],
    },
    
    include_package_data=True,

    # # To provide executable scripts, use entry points in preference to the
    # # "scripts" keyword. Entry points provide cross-platform support and allow
    # # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'agentserver=agentserver.server:main',
            'agentserveradmin=agentserver.admin:main',
            'agentserverecho=agentserver.echo:main'
        ],
    },
)
