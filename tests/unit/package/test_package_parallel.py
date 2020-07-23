import os
import traceback

import py
from flaky import flaky

from tox.session.commands.run import sequential


@flaky(max_runs=3)
def test_tox_parallel_build_safe(initproj, cmd, mock_venv, monkeypatch):
    initproj(
        "env_var_test",
        filedefs={
            "tox.ini": """
                  [tox]
                  envlist = py
                  install_cmd = python -m -c 'print("ok")' -- {opts} {packages}'
                  [testenv]
                  commands = python -c 'import sys; print(sys.version)'
                      """,
        },
    )
    # we try to recreate the following situation
    # t1 starts and performs build
    # t2 starts, but is blocked from t1 build lock to build
    # t1 gets unblocked, t2 can now enter
    # t1 is artificially blocked to run test command until t2 finishes build
    #  (parallel build package present)
    # t2 package build finishes both t1 and t2 can now finish and clean up their build packages
    import threading

    import tox.package

    t1_build_started = threading.Event()
    t1_build_blocker = threading.Event()
    t2_build_started = threading.Event()
    t2_build_finished = threading.Event()

    invoke_result = {}

    def invoke_tox_in_thread(thread_name):
        try:
            result = cmd("--parallel--safe-build", "-vv")
        except Exception as exception:
            result = exception, traceback.format_exc()
        invoke_result[thread_name] = result

    prev_build_package = tox.package.build_package

    with monkeypatch.context() as m:

        def build_package(config, session):
            t1_build_started.set()
            t1_build_blocker.wait()
            return prev_build_package(config, session)

        m.setattr(tox.package, "build_package", build_package)

        prev_run_test_env = sequential.runtestenv

        def run_test_env(venv, redirect=False):
            t2_build_finished.wait()
            return prev_run_test_env(venv, redirect)

        m.setattr(sequential, "runtestenv", run_test_env)

        t1 = threading.Thread(target=invoke_tox_in_thread, args=("t1",))
        t1.start()
        t1_build_started.wait()

    with monkeypatch.context() as m:

        def build_package(config, session):
            t2_build_started.set()
            try:
                return prev_build_package(config, session)
            finally:
                t2_build_finished.set()

        m.setattr(tox.package, "build_package", build_package)

        t2 = threading.Thread(target=invoke_tox_in_thread, args=("t2",))
        t2.start()

        # t2 should get blocked by t1 build lock
        t2_build_started.wait(timeout=0.1)
        assert not t2_build_started.is_set()

        t1_build_blocker.set()  # release t1 blocker -> t1 can now finish
        # t1 at this point should block at run test until t2 build finishes
        t2_build_started.wait()

    t1.join()  # wait for both t1 and t2 to finish
    t2.join()

    # all threads finished without error
    for val in invoke_result.values():
        if isinstance(val, tuple):
            assert False, "{!r}\n{}".format(val[0], val[1])
    err = "\n".join(
        "{}=\n{}".format(k, v.err).strip() for k, v in invoke_result.items() if v.err.strip()
    )
    out = "\n".join(
        "{}=\n{}".format(k, v.out).strip() for k, v in invoke_result.items() if v.out.strip()
    )
    for val in invoke_result.values():
        assert not val.ret, "{}\n{}".format(err, out)
    assert not err

    # when the lock is hit we notify
    lock_file = py.path.local().join(".tox", ".package.lock")
    msg = "lock file {} present, will block until released".format(lock_file)
    assert msg in out

    # intermediate packages are removed at end of build
    t1_package = invoke_result["t1"].session.getvenv("py").package
    t2_package = invoke_result["t1"].session.getvenv("py").package
    assert t1 != t2
    assert not t1_package.exists()
    assert not t2_package.exists()

    # the final distribution remains
    dist_after = invoke_result["t1"].session.config.distdir.listdir()
    assert len(dist_after) == 1
    sdist = dist_after[0]
    assert t1_package != sdist
    # our set_os_env_var is not thread-safe so clean-up TOX_WORK_DIR
    os.environ.pop("TOX_WORK_DIR", None)
