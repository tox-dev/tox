def test_parallel_inception(initproj, cmd):
    initproj(
        "inception-1.2.3",
        filedefs={
            # the outer config just has one env: graham
            "tox.ini": """
            [tox]
            envlist = graham
            skipsdist = True

            [testenv]
            commands =
                python runner.py
            """,
            # the inner config has 3 different envs, 1 of them is graham
            "inner": {
                "tox.ini": """
                [tox]
                envlist = graham,john,terry
                skipsdist = True

                [testenv]
                commands =
                    python -c 'pass'
                """,
            },
            # the outer test runs the inner tox and asserts all 3 envs were run
            "runner.py": """
            import os
            import subprocess
            import sys

            os.chdir("inner")
            p = subprocess.Popen(("tox"), stdout=subprocess.PIPE, universal_newlines=True)
            stdout, _ = p.communicate()
            sys.stdout.write(stdout)
            assert "graham" in stdout
            assert "john" in stdout
            assert "terry" in stdout
            """,
        },
        add_missing_setup_py=False,
    )

    result = cmd("-p", "all", "-o")
    result.assert_success()

    # 1 from the outer, 1 from the inner
    assert result.out.count("graham: commands succeeded") == 2
    # those gentlemen are only inside
    assert result.out.count("john: commands succeeded") == 1
    assert result.out.count("terry: commands succeeded") == 1
