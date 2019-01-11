# FIXME this seems unnecessary
# TODO move fixtures here and only keep helper functions/classes in the plugin
# TODO _pytest_helpers might be a better name than _pytestplugin then?
# noinspection PyUnresolvedReferences
import tox.venv
from tox._pytestplugin import *  # noqa

tox.venv.NO_DOWNLOAD = True
