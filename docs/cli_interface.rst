.. _cli:

###############
 CLI interface
###############

******************
 Shell completion
******************

tox supports shell completion for commands, flags, and environment names via :pypi:`argcomplete`. Install tox with the
``completion`` extra:

.. code-block:: bash

    uv tool install 'tox[completion]'

Then configure your shell:

.. tab:: bash

    Add to ``~/.bashrc``:

    .. code-block:: bash

       eval "$(register-python-argcomplete tox)"

.. tab:: zsh

    Add to ``~/.zshrc``:

    .. code-block:: zsh

       autoload -U bashcompinit
       bashcompinit
       eval "$(register-python-argcomplete tox)"

.. tab:: fish

    Add to ``~/.config/fish/config.fish``:

    .. code-block:: fish

       register-python-argcomplete --shell fish tox | source

Once configured, pressing ``<TAB>`` completes subcommands (``tox r`` → ``tox run``), flags (``tox run --``), and
environment names (``tox run -e`` lists environments from your tox configuration).

**********************
 Command-line options
**********************

.. sphinx_argparse_cli::
    :module: tox.config.cli.parse
    :func: _get_parser_doc
