from tox.pytest import ToxProjectCreator


def test_depends(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.ini": """
    [tox]
    env_list = py39,py38,py37,cov2,cov
    [testenv]
    package = wheel
    [testenv:cov]
    depends = py39,py38,py37
    skip_install = true
    [testenv:cov2]
    depends = cov
    skip_install = true
    """
        }
    )
    outcome = project.run("de")
    outcome.assert_success()
    out = """Execution order: py39, py38, py37, cov, cov2
ALL
   py39 ~ .package-py39
   py38 ~ .package-py38
   py37 ~ .package-py37
   cov2
      cov
         py39 ~ .package-py39
         py38 ~ .package-py38
         py37 ~ .package-py37
   cov
      py39 ~ .package-py39
      py38 ~ .package-py38
      py37 ~ .package-py37
    """
    outcome.assert_out_err(out, "")
