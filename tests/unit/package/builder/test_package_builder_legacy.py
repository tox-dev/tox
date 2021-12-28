def test_verbose_legacy_build(initproj, mock_venv, cmd):
    initproj(
        "example123-0.5",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = false
                    """,
        },
    )
    result = cmd("--sdistonly", "-vvv", "-e", "py")
    assert "running sdist" in result.out, result.out
    assert "running egg_info" in result.out, result.out
    assert "removing 'example123-0.5'" in result.out, result.out
