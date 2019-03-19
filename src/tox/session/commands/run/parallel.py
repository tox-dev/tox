from collections import OrderedDict

import inspect
import os
import signal
import subprocess
import sys
import tempfile
from threading import Event, Semaphore, Thread

from tox import __main__ as main
from tox import reporter
from tox.config.parallel import ENV_VAR_KEY as PARALLEL_ENV_VAR_KEY
from tox.util.spinner import Spinner
from tox.util.stdlib import nullcontext

MAIN_FILE = inspect.getsourcefile(main)


def run_parallel(config, venv_dict):
    """here we'll just start parallel sub-processes"""
    live_out = config.option.parallel_live
    args = [sys.executable, MAIN_FILE] + config.args
    try:
        position = args.index("--")
    except ValueError:
        position = len(args)

    max_parallel = config.option.parallel
    if max_parallel is None:
        max_parallel = len(venv_dict)
    semaphore = Semaphore(max_parallel)
    finished = Event()

    ctx = nullcontext if live_out else tempfile.NamedTemporaryFile
    stderr = None if live_out else subprocess.STDOUT

    show_progress = not live_out and reporter.verbosity() > reporter.Verbosity.QUIET
    with Spinner(enabled=show_progress) as spinner, ctx() as sink:

        def run_in_thread(tox_env, os_env, processes):
            res = None
            env_name = tox_env.envconfig.envname
            try:
                os_env[str(PARALLEL_ENV_VAR_KEY)] = str(env_name)
                args_sub = list(args)
                if hasattr(tox_env, "package"):
                    args_sub.insert(position, str(tox_env.package))
                    args_sub.insert(position, "--installpkg")
                process = subprocess.Popen(
                    args_sub,
                    env=os_env,
                    stdout=sink,
                    stderr=stderr,
                    stdin=None,
                    universal_newlines=True,
                )
                processes[env_name] = process
                reporter.verbosity2("started {} with pid {}".format(env_name, process.pid))
                res = process.wait()
            finally:
                semaphore.release()
                finished.set()
                tox_env.status = (
                    "skipped tests"
                    if config.option.notest
                    else ("parallel child exit code {}".format(res) if res else res)
                )
                done.add(env_name)
                outcome = spinner.succeed
                if config.option.notest:
                    outcome = spinner.skip
                elif res:
                    outcome = spinner.fail
                outcome(env_name)

            if not live_out:
                sink.seek(0)
                out = sink.read().decode("UTF-8", errors="replace")
                if res or tox_env.envconfig.parallel_show_output:
                    outcome = (
                        "Failed {} under process {}, stdout:\n".format(env_name, process.pid)
                        if res
                        else ""
                    )
                    message = "{}{}".format(outcome, out).rstrip()
                    reporter.quiet(message)

        threads = []
        processes = {}
        todo_keys = set(venv_dict.keys())
        todo = OrderedDict((n, todo_keys & set(v.envconfig.depends)) for n, v in venv_dict.items())
        done = set()
        try:
            while todo:
                for name, depends in list(todo.items()):
                    if depends - done:
                        # skip if has unfinished dependencies
                        continue
                    del todo[name]
                    venv = venv_dict[name]
                    semaphore.acquire(blocking=True)
                    spinner.add(name)
                    thread = Thread(
                        target=run_in_thread, args=(venv, os.environ.copy(), processes)
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
                if todo:
                    # wait until someone finishes and retry queuing jobs
                    finished.wait()
                    finished.clear()
            for thread in threads:
                while thread.is_alive():
                    thread.join(0.05)
                    # join suspends signal handling (ctrl+c), periodically time-out to check for it
        except KeyboardInterrupt:
            reporter.verbosity0("keyboard interrupt parallel - stopping children")
            while True:
                # do not allow to interrupt until children interrupt
                try:
                    # first try to request a graceful shutdown
                    for name, proc in list(processes.items()):
                        if proc.returncode is None:
                            proc.send_signal(
                                signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT
                            )
                            reporter.verbosity2("send CTRL+C {}-{}".format(name, proc.pid))
                    if len(threads):
                        threads[0].join(1.2)  # wait at most 200ms for all to finish

                    # now if being gentle did not work now be forceful
                    for name, proc in list(processes.items()):
                        if proc.returncode is None:
                            proc.terminate()
                            reporter.verbosity2("terminate {}-{}".format(name, proc.pid))
                    for thread in threads:
                        thread.join()
                except KeyboardInterrupt:
                    continue
                raise KeyboardInterrupt
