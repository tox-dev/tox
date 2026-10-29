A ``pylock.toml`` that is not valid TOML -- for example one with a syntax error, or bytes that are not UTF-8 -- now
fails with an ``invalid pylock file`` error naming the problem instead of an internal error traceback.
