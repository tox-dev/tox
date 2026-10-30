An invalid ``pylock.toml``, including malformed TOML or non-UTF-8 bytes, now reports ``invalid pylock file`` with the
filename and the parser or decoder error instead of an internal traceback.
