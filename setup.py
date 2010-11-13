import sys
from setuptools import setup

long_description="""
What is Tox?
==========================

Tox as is a generic virtualenv management and test command line tool you can
use for:

* checking your package installs correctly with different
  Python versions and interpreters

* running your tests in each of the
  environments, configuring your test tool of choice

* acting as a frontend to Continous Integration
  servers, greatly reducing boilerplate and merging
  CI and shell-based testing.

For more information, docs and many examples please checkout the `home page`_:

http://codespeak.net/tox

.. _`home page`: http://codespeak.net/tox
"""


def main():
    install_requires=['virtualenv5>=1.3.4.5']
    if sys.version_info[0] < 3:
        install_requires+=['virtualenv>=1.4.9']
    setup(
        name='tox',
        description='virtualenv-based automation of test activities',
        long_description=long_description,
        url='http://codespeak.net/tox',
        version='0.9.dev9',
        license='GPLv2 or later',
        platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
        author='holger krekel',
        author_email='holger@merlinux.eu',
        packages=['tox', ],
        entry_points={'console_scripts': 'tox=tox:cmdline'},
        install_requires=install_requires+['argparse', 'pylib>=1.9.9', ],
        zip_safe=True,
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: GNU General Public License (GPL)',
             'Operating System :: POSIX',
             'Operating System :: Microsoft :: Windows',
             'Operating System :: MacOS :: MacOS X',
             'Topic :: Software Development :: Testing',
             'Topic :: Software Development :: Libraries',
             'Topic :: Utilities',
             'Programming Language :: Python',
             'Programming Language :: Python :: 3'],
    )

if __name__ == '__main__':
    main()
