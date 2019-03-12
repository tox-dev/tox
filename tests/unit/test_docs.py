import os.path
import re
import textwrap

import pytest

import tox
from tox.config import parseconfig

INI_BLOCK_RE = re.compile(
    r"(?P<before>"
    r"^(?P<indent> *)\.\. (code-block|sourcecode):: ini\n"
    r"((?P=indent) +:.*\n)*"
    r"\n*"
    r")"
    r"(?P<code>(^((?P=indent) +.*)?\n)+)",
    re.MULTILINE,
)


RST_FILES = []
TOX_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
for root, _, filenames in os.walk(os.path.join(TOX_ROOT, "docs")):
    for filename in filenames:
        if filename.endswith(".rst"):
            RST_FILES.append(os.path.join(root, filename))


def test_some_files_exist():
    assert RST_FILES


@pytest.mark.parametrize("filename", RST_FILES)
def test_all_rst_ini_blocks_parse(filename, tmpdir):
    with open(filename) as f:
        contents = f.read()
    for match in INI_BLOCK_RE.finditer(contents):
        code = textwrap.dedent(match.group("code"))
        config_path = tmpdir / "tox.ini"
        config_path.write(code)
        try:
            parseconfig(["-c", str(config_path)])
        except tox.exception.MissingRequirement:
            pass
        except Exception as e:
            raise AssertionError(
                "Error parsing ini block\n\n"
                "{filename}:{lineno}\n\n"
                "{code}\n\n"
                "{error}\n\n{error!r}".format(
                    filename=filename,
                    lineno=contents[: match.start()].count("\n") + 1,
                    code="\t" + code.replace("\n", "\n\t").strip(),
                    error=e,
                )
            )
