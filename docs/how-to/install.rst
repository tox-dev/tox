##############
 Installation
##############

*********
 As tool
*********

:pypi:`tox` is a CLI tool that needs a Python interpreter (version 3.10 or higher) to run. We recommend either
:pypi:`pipx` or :pypi:`uv` to install tox into an isolated environment. This has the added benefit that later you'll be
able to upgrade tox without affecting other parts of the system. We provide method for ``pip`` too here but we
discourage that path if you can:

.. tab:: uv

    .. code-block:: bash

        # install uv per https://docs.astral.sh/uv/#getting-started
        uv tool install tox
        tox --help

.. tab:: pipx

    .. code-block:: bash

        python -m pip install pipx-in-pipx --user
        pipx install tox
        tox --help

.. tab:: pip

    .. code-block:: bash

        python -m pip install --user tox
        python -m tox --help

    You can install it within the global Python interpreter itself (perhaps as a user package via the
    ``--user`` flag). Be cautious if you are using a Python installation that is managed by your operating system or
    another package manager. ``pip`` might not coordinate with those tools, and may leave your system in an inconsistent
    state.

    **Requirements:**

    - **wheel (default):** Installing tox via a wheel requires pip that understands the ``python-requires`` tag (see
      :PEP:`503`). With pip this is version ``9.0.0`` or later (released November 2016). If installing from a mirror,
      ensure it forwards the ``python-requires`` tag (notably OpenStack mirrors don't, and older :gh_repo:`devpi/devpi`
      versions before ``4.7.0`` don't).

    .. _sdist:

    - **sdist:** When installing via a source distribution you need pip that handles :PEP:`517`. With pip this is
      version ``18.0.0`` or later (released July 2018). If you cannot upgrade pip, ensure the build requirements from
      :gh:`pyproject.toml <tox-dev/tox/blob/main/pyproject.toml>` are satisfied before installation.

*******************
 latest unreleased
*******************

Installing an unreleased version is discouraged and should be only done for testing purposes:

.. tab:: uv

    .. code-block:: bash

        uv tool install --from git+https://github.com/tox-dev/tox.git@main tox

.. tab:: pipx

    .. code-block:: bash

        pipx install git+https://github.com/tox-dev/tox.git@main

.. tab:: pip

    .. code-block:: bash

        pip install git+https://github.com/tox-dev/tox.git@main

    Requires pip version ``18.0.0`` or later.

For Python version compatibility, see :ref:`compatibility-requirements`.

******************
 Man Page Support
******************

tox includes a Unix man page that is automatically built when building documentation. The man page provides
comprehensive reference documentation for all tox commands and options.

Automatic Installation
======================

The man page is pre-built and included in tox wheels. When installing tox:

- **System-wide** (``sudo pip install tox``): Installs to ``/usr/share/man/man1/tox.1`` automatically
- **User install** (``pip install --user tox``): Installs to ``~/.local/share/man/man1/tox.1`` automatically
- **Package managers** (apt, brew, dnf): Install to the appropriate system location

For user installs, ensure ``~/.local/share/man`` is in your ``MANPATH``:

.. code-block:: bash

    # Add to ~/.bashrc or ~/.zshrc
    export MANPATH="$HOME/.local/share/man:$MANPATH"

After updating your profile, restart your shell or run ``source ~/.bashrc``.

Virtualenv Installations
========================

When tox is installed in a virtualenv (via pipx, uv tool, or venv), the man page is installed but not on the system
``MANPATH``. Use the ``tox man`` command to set it up automatically:

.. code-block:: bash

    tox man

This command will:

- Check if the man page is accessible
- Create a symlink from the virtualenv to ``~/.local/share/man/man1/``
- Detect your shell and provide instructions for adding ``MANPATH`` to your profile

Alternatively, you can set it up manually:

.. code-block:: bash

    # Find where tox is installed
    TOX_PREFIX=$(python -c "import sys; print(sys.prefix)")

    # Create symlink to user man directory
    mkdir -p ~/.local/share/man/man1
    ln -sf "$TOX_PREFIX/share/man/man1/tox.1" ~/.local/share/man/man1/tox.1

    # Ensure MANPATH includes user directory (if not already set)
    export MANPATH="$HOME/.local/share/man:$MANPATH"

Building from Source
====================

Package maintainers building from source can generate the man page using Sphinx:

.. code-block:: bash

    # Build documentation (includes man page)
    tox run -e docs

    # Man page is generated at .tox/docs_out/man/tox.1
    # Install to system location
    install -D -m 644 .tox/docs_out/man/tox.1 /usr/share/man/man1/tox.1
    gzip -9 /usr/share/man/man1/tox.1

Viewing the Man Page
====================

After installation:

.. code-block:: bash

    man tox

For virtualenv-based installations where the man page is not on ``MANPATH``, use ``tox --help`` instead.
