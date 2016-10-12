import sys
import setuptools
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

def has_environment_marker_support():
    """
    Tests that setuptools has support for PEP-426 environment marker support.

    The first known release to support it is 0.7 (and the earliest on PyPI seems to be 0.7.2
    so we're using that), see: http://pythonhosted.org/setuptools/history.html#id142

    References:

    * https://wheel.readthedocs.org/en/latest/index.html#defining-conditional-dependencies
    * https://www.python.org/dev/peps/pep-0426/#environment-markers
    """
    import pkg_resources
    try:
        return pkg_resources.parse_version(setuptools.__version__) >= pkg_resources.parse_version('0.7.2')
    except Exception as exc:
        sys.stderr.write("Could not test setuptool's version: %s\n" % exc)
        return False

def main():
    version = sys.version_info[:2]
    install_requires = ['virtualenv>=1.11.2', 'py>=1.4.17', 'pluggy>=0.3.0,<0.5.0']
    extras_require = {}
    if has_environment_marker_support():
        extras_require[':python_version=="2.6"'] = ['argparse']
    else:
        if version < (2, 7):
            install_requires += ['argparse']
    setuptools.setup(
        name='tox',
        description='virtualenv-based automation of test activities',
        long_description=open("README.rst").read(),
        url='https://tox.readthedocs.org/',
        version='2.4.1',
        license='http://opensource.org/licenses/MIT',
        platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
        author='holger krekel',
        author_email='holger@merlinux.eu',
        packages=['tox'],
        entry_points={'console_scripts': 'tox=tox:cmdline\ntox-quickstart=tox._quickstart:main'},
        # we use a public tox version to test, see tox.ini's testenv
        # "deps" definition for the required dependencies
        tests_require=['tox'],
        cmdclass={"test": Tox},
        install_requires=install_requires,
        extras_require=extras_require,
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
