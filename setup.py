import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand



class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ["-v", "-epy"]
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import tox
        tox.cmdline(self.test_args)


def main():
    version = sys.version_info[:2]
    install_requires = ['virtualenv>=1.11.2', 'py>=1.4.17', ]
    if version < (2, 7) or (3, 0) <= version <= (3, 1):
        install_requires += ['argparse']
    if version < (2,6):
        install_requires += ["simplejson"]
    setup(
        name='tox',
        description='virtualenv-based automation of test activities',
        long_description=open("README.rst").read(),
        url='http://tox.testrun.org/',
        version='1.8.0.dev1',
        license='http://opensource.org/licenses/MIT',
        platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
        author='holger krekel',
        author_email='holger@merlinux.eu',
        packages=['tox', 'tox.vendor'],
        entry_points={'console_scripts': 'tox=tox:cmdline\ntox-quickstart=tox._quickstart:main'},
        # we use a public tox version to test, see tox.ini's testenv
        # "deps" definition for the required dependencies
        tests_require=['tox'],
        cmdclass={"test": Tox},
        install_requires=install_requires,
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
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
