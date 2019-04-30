def test_listenvs(cmd, initproj, monkeypatch):
    monkeypatch.delenv(str("TOXENV"), raising=False)
    initproj(
        "listenvs",
        filedefs={
            "tox.ini": """
        [tox]
        envlist=py36,py27,py34,pypi,docs
        description= py27: run pytest on Python 2.7
                     py34: run pytest on Python 3.6
                     pypi: publish to PyPI
                     docs: document stuff
                     notincluded: random extra

        [testenv:notincluded]
        changedir = whatever

        [testenv:docs]
        changedir = docs
        """
        },
    )

    result = cmd("-l")
    assert result.outlines == ["py36", "py27", "py34", "pypi", "docs"]

    result = cmd("-l", "-e", "py")
    assert result.outlines == ["py36", "py27", "py34", "pypi", "docs"]

    monkeypatch.setenv(str("TOXENV"), str("py"))
    result = cmd("-l")
    assert result.outlines == ["py36", "py27", "py34", "pypi", "docs"]

    monkeypatch.setenv(str("TOXENV"), str("py36"))
    result = cmd("-l")
    assert result.outlines == ["py36", "py27", "py34", "pypi", "docs"]


def test_listenvs_verbose_description(cmd, initproj):
    initproj(
        "listenvs_verbose_description",
        filedefs={
            "tox.ini": """
        [tox]
        envlist=py36,py27,py34,pypi,docs
        [testenv]
        description= py36: run pytest on Python 3.6
                     py27: run pytest on Python 2.7
                     py34: run pytest on Python 3.4
                     pypi: publish to PyPI
                     docs: document stuff
                     notincluded: random extra

        [testenv:notincluded]
        changedir = whatever

        [testenv:docs]
        changedir = docs
        description = let me overwrite that
        """
        },
    )
    result = cmd("-lv")
    expected = [
        "default environments:",
        "py36 -> run pytest on Python 3.6",
        "py27 -> run pytest on Python 2.7",
        "py34 -> run pytest on Python 3.4",
        "pypi -> publish to PyPI",
        "docs -> let me overwrite that",
    ]
    assert result.outlines[2:] == expected


def test_listenvs_all(cmd, initproj, monkeypatch):
    initproj(
        "listenvs_all",
        filedefs={
            "tox.ini": """
        [tox]
        envlist=py36,py27,py34,pypi,docs

        [testenv:notincluded]
        changedir = whatever

        [testenv:docs]
        changedir = docs
        """
        },
    )
    result = cmd("-a")
    expected = ["py36", "py27", "py34", "pypi", "docs", "notincluded"]
    assert result.outlines == expected

    result = cmd("-a", "-e", "py")
    assert result.outlines == ["py36", "py27", "py34", "pypi", "docs", "py", "notincluded"]

    monkeypatch.setenv(str("TOXENV"), str("py"))
    result = cmd("-a")
    assert result.outlines == ["py36", "py27", "py34", "pypi", "docs", "py", "notincluded"]

    monkeypatch.setenv(str("TOXENV"), str("py36"))
    result = cmd("-a")
    assert result.outlines == ["py36", "py27", "py34", "pypi", "docs", "notincluded"]


def test_listenvs_all_verbose_description(cmd, initproj):
    initproj(
        "listenvs_all_verbose_description",
        filedefs={
            "tox.ini": """
        [tox]
        envlist={py27,py36}-{windows,linux} # py35
        [testenv]
        description= py27: run pytest on Python 2.7
                     py36: run pytest on Python 3.6
                     windows: on Windows platform
                     linux: on Linux platform
                     docs: generate documentation
        commands=pytest {posargs}

        [testenv:docs]
        changedir = docs
        """
        },
    )
    result = cmd("-av")
    expected = [
        "default environments:",
        "py27-windows -> run pytest on Python 2.7 on Windows platform",
        "py27-linux   -> run pytest on Python 2.7 on Linux platform",
        "py36-windows -> run pytest on Python 3.6 on Windows platform",
        "py36-linux   -> run pytest on Python 3.6 on Linux platform",
        "",
        "additional environments:",
        "docs         -> generate documentation",
    ]
    assert result.outlines[-len(expected) :] == expected


def test_listenvs_all_verbose_description_no_additional_environments(cmd, initproj):
    initproj(
        "listenvs_all_verbose_description",
        filedefs={
            "tox.ini": """
        [tox]
        envlist=py27,py36
        """
        },
    )
    result = cmd("-av")
    expected = ["default environments:", "py27 -> [no description]", "py36 -> [no description]"]
    assert result.out.splitlines()[-3:] == expected
    assert "additional environments" not in result.out


def test_listenvs_packaging_excluded(cmd, initproj):
    initproj(
        "listenvs",
        filedefs={
            "tox.ini": """
        [tox]
        envlist = py36,py27,py34,pypi,docs
        isolated_build = True

        [testenv:notincluded]
        changedir = whatever

        [testenv:docs]
        changedir = docs
        """
        },
    )
    result = cmd("-a")
    expected = ["py36", "py27", "py34", "pypi", "docs", "notincluded"]
    assert result.outlines == expected, result.outlines


def test_listenvs_all_extra_definition_order_decreasing(cmd, initproj):
    initproj(
        "listenvs_all",
        filedefs={
            "tox.ini": """
        [tox]
        envlist=py36

        [testenv:b]
        changedir = whatever

        [testenv:a]
        changedir = docs
        """
        },
    )
    result = cmd("-a")
    expected = ["py36", "b", "a"]
    assert result.outlines == expected


def test_listenvs_all_extra_definition_order_increasing(cmd, initproj):
    initproj(
        "listenvs_all",
        filedefs={
            "tox.ini": """
        [tox]
        envlist=py36

        [testenv:a]
        changedir = whatever

        [testenv:b]
        changedir = docs
        """
        },
    )
    result = cmd("-a")
    expected = ["py36", "a", "b"]
    assert result.outlines == expected
