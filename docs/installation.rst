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
    state. Note, if you go down this path you need to ensure pip is new enough per the subsections below

wheel
=====

Installing tox via a wheel (default with pip) requires an installer that can understand the ``python-requires`` tag (see
:PEP:`503`), with pip this is version ``9.0.0`` (released in November 2016). Furthermore, in case you're not installing
it via PyPI you need to use a mirror that correctly forwards the ``python-requires`` tag (notably the OpenStack mirrors
don't do this, or older :gh_repo:`devpi/devpi` versions - added with version ``4.7.0``).

.. _sdist:

sdist
=====

When installing via a source distribution you need an installer that handles the :PEP:`517` specification. In case of
``pip`` this is version ``18.0.0`` or later (released in July 2018). If you cannot upgrade your pip to support this you
need to ensure that the build requirements from :gh:`pyproject.toml <tox-dev/tox/blob/main/pyproject.toml>` are
satisfied before triggering the installation.

*******************
 latest unreleased
*******************

Installing an unreleased version is discouraged and should be only done for testing purposes. If you do so you'll need a
pip version of at least ``18.0.0`` and use the following command:

.. code-block:: bash

    pip install git+https://github.com/tox-dev/tox.git@main

.. _compatibility-requirements:

*****************************
 Python and OS Compatibility
*****************************

tox works with the following Python interpreter implementations:

- `CPython <https://www.python.org/>`_ versions 3.10, 3.11, 3.12, 3.13, 3.14

This means tox works on the latest patch version of each of these minor versions. Previous patch versions are supported
on a best effort approach.

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
