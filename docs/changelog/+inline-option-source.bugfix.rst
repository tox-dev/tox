Validate built-in command options before selecting an inline plugin. An invalid option value no longer causes tox to
import a plugin from an unselected project. Put ``-c``/``--conf`` or ``--root`` before options defined by an inline
plugin.
