import subprocess
import sys

from tox import reporter as report
from tox.version import __version__


def show_config(config):
    info_versions()
    report.keyvalue("config-file:", config.option.configfile)
    report.keyvalue("toxinipath: ", config.toxinipath)
    report.keyvalue("toxinidir:  ", config.toxinidir)
    report.keyvalue("toxworkdir: ", config.toxworkdir)
    report.keyvalue("setupdir:   ", config.setupdir)
    report.keyvalue("distshare:  ", config.distshare)
    report.keyvalue("skipsdist:  ", config.skipsdist)
    report.line("")
    for envconfig in config.envconfigs.values():
        report.line("[testenv:{}]".format(envconfig.envname), bold=True)
        for attr in config._parser._testenv_attr:
            report.line("  {:<15} = {}".format(attr.name, getattr(envconfig, attr.name)))


def info_versions():
    versions = ["tox-{}".format(__version__)]
    proc = subprocess.Popen(
        (sys.executable, "-m", "virtualenv", "--version"), stdout=subprocess.PIPE
    )
    out, _ = proc.communicate()
    versions.append("virtualenv-{}".format(out.decode("UTF-8").strip()))
    report.keyvalue("tool-versions:", " ".join(versions))
