With ``TOX_LIMITED_SHEBANG`` enabled, tox now keeps quote and backslash characters in an unquoted shebang interpreter
path. They no longer change the executable tox starts. The existing double-quoted form for paths with spaces remains
supported.
