"""In case the tox environment is not correctly setup provision it and delegate execution"""
from __future__ import absolute_import, unicode_literals


def provision_tox(provision_venv, args):
    ensure_meta_env_up_to_date(provision_venv)
    with provision_venv.new_action("provision") as action:
        provision_args = [str(provision_venv.envconfig.envpython), "-m", "tox"] + args
        action.popen(provision_args, redirect=False)


def ensure_meta_env_up_to_date(provision_venv):
    if provision_venv.setupenv():
        provision_venv.finishvenv()
