import py
import subprocess
def test_linkcheck(tmpdir):
    py.path.local(__file__).dirpath().chdir()
    
    doctrees = tmpdir.join("doctrees")
    htmldir = tmpdir.join("html")
    subprocess.check_call(
        ["sphinx-build", "-W", "-blinkcheck", 
          "-d", str(doctrees), ".", str(htmldir)])

def test_build_docs(tmpdir):
    py.path.local(__file__).dirpath().chdir()
    doctrees = tmpdir.join("doctrees")
    htmldir = tmpdir.join("html")
    subprocess.check_call([
        "sphinx-build", "-W", "-bhtml", 
          "-d", str(doctrees), ".", str(htmldir)])

