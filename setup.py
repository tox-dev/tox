import sys
from setuptools import setup

def main():
    install_requires=['virtualenv3']
    if sys.version_info[0] < 3:
        install_requires+=['virtualenv']
    setup(
        name='tox',
        description='automating packaging, testing & release',
        url='http://codespeak.net/tox',
        version='0.5',
        license='GPLv2 or later',
        platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
        author='holger krekel',
        author_email='holger@merlinux.eu',
        packages=['tox', ],
        entry_points={'console_scripts': 'tox=tox:cmdline'},
        install_requires=install_requires+['argparse', 'apipkg', 'py', ],
        zip_safe=True,
    )

if __name__ == '__main__':
    main()

