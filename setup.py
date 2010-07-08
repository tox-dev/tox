import sys
from setuptools import setup

def main():
    install_requires=['virtualenv3==1.3.4.1']
    if sys.version_info[0] < 3:
        install_requires+=['virtualenv']
    setup(
        name='tox',
        description='virtualenv-based automation of test activities',
        url='http://codespeak.net/tox',
        version='0.5a2',
        license='GPLv2 or later',
        platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
        author='holger krekel',
        author_email='holger@merlinux.eu',
        packages=['tox', ],
        entry_points={'console_scripts': 'tox=tox:cmdline'},
        install_requires=install_requires+['argparse', 'apipkg', 'py', ],
        zip_safe=True,
        classifiers=[
            'Development Status :: 3 - Alpha',
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

