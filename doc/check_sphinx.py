import py
import subprocess
def test_build_docs(tmpdir):
    doctrees = tmpdir.join("doctrees")
    htmldir = tmpdir.join("html")
    subprocess.check_call([
        "sphinx-build", "-bhtml", '-W',
          "-d", str(doctrees), ".", str(htmldir)])

def test_linkcheck(tmpdir):
    doctrees = tmpdir.join("doctrees")
    htmldir = tmpdir.join("html")
    subprocess.check_call(
        ["sphinx-build", "-blinkcheck", '-W',
          "-d", str(doctrees), ".", str(htmldir)])


