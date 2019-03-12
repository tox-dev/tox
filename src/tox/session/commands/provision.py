"""In case the tox environment is not correctly setup provision it and delegate execution"""
import signal
import subprocess


def provision_tox(provision_venv, args):
    ensure_meta_env_up_to_date(provision_venv)
    process = start_meta_tox(args, provision_venv)
    result_out = wait_for_meta_tox(process)
    raise SystemExit(result_out)


def ensure_meta_env_up_to_date(provision_venv):
    if provision_venv.setupenv():
        provision_venv.finishvenv()


def start_meta_tox(args, provision_venv):
    provision_args = [str(provision_venv.envconfig.envpython), "-m", "tox"] + args
    process = subprocess.Popen(provision_args)
    return process


def wait_for_meta_tox(process):
    try:
        result_out = process.wait()
    except KeyboardInterrupt:
        # if we try to interrupt delegate interrupt to meta tox
        process.send_signal(signal.SIGINT)
        result_out = process.wait()
    return result_out
