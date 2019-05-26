FROM ubuntu:18.04

# Set the default shell to bash instead of sh
ENV SHELL /bin/bash

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG C.UTF-8

# Install python versions from deadsnakes used in linux CI
RUN . /etc/os-release && \
    apt-get update && \
    apt-get install -y gnupg && \
    echo "deb http://ppa.launchpad.net/deadsnakes/ppa/ubuntu ${UBUNTU_CODENAME} main" > /etc/apt/sources.list.d/deadsnakes.list && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt-get update && \
    apt-get install -y \
        python-pip python3-pip \
        \
        python2.7 python2.7-dev \
        python3.[4,5,6,7] python3.[4,5,6,7]-dev \
    && \
    apt-get --purge autoremove -y gnupg && \
    apt-get clean -y && \
    rm -rf /var/cache/apt/lists/*

# Install git, process tools (needed by vscode remote)
# gcc and ca-cert needed to install dev envs. Do clean up at the end
RUN apt-get update && \
    apt-get install -y \
        git procps \
        gcc ca-cacert \
        vim htop \
    && \
    apt-get --purge autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install tox
RUN python3.7 -m pip install --upgrade pip && python3.7 -m pip install tox

# Copy default endpoint specific user settings overrides into container to specify default python path,
# virtualenvs from tox to use as python interpreters and pytest settings
COPY .devcontainer/settings.vscode.json /root/.vscode-remote/data/Machine/settings.json

# For some reason terminal opened inside vscode is settings LANG='en_US.UTF8' and some tests
# are failing because of http://bugs.python.org/issue19846
# Added also some useful aliases and env variable to run test in parallel
# Set tox workdir ~/.tox by default to don't pollute the source code, keeps venvs inside container
# and install them faster (no access to mounted volume).
# vscode is reusing the container unless you rebuild it. Any other tox environments will survive until
# next rebuild
RUN echo "\
export LANG='C.UTF-8'\n\
export PYTEST_ADDOPTS='-n auto'\n\
alias tox='tox --workdir ~/.tox'\n\
alias workon_dev='. ~/.tox/dev/bin/activate'\n\
" >> ~/.bashrc
