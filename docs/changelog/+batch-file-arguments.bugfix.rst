On Windows, tox quotes arguments passed to ``.bat`` and ``.cmd`` commands for ``cmd.exe``. Values containing shell
operators or percent signs reach the batch file without starting another command or expanding environment variables.
Batch scripts that inspect raw ``%1`` may now see surrounding quotes for arguments that need them.
