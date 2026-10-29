An included ``set_env`` keeps ``{env:...}`` values intact when the source environment inherits the setting, uses
``setenv`` or comes from a generative section. The TOML string form ``"{[env.name]set_env}"`` does the same.
Line breaks, ``;`` and ``file|`` text inside values no longer become ``set_env`` syntax.
