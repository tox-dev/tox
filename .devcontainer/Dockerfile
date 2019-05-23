#-------------------------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See https://go.microsoft.com/fwlink/?linkid=2090316 for license information.
#-------------------------------------------------------------------------------------------------------------

FROM python:3-slim-stretch

# Set the default shell to bash instead of sh
ENV SHELL /bin/bash

# Install git, process tools (needed by vscode remote) and remaining tools to complete dev env. Do clean up at the end
RUN apt-get update && apt-get -y install git procps\
    && apt-get -y install gcc python2.7-dev python3.5-dev pypy-dev vim htop\
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install tox
RUN python -m pip install tox

# Copy default endpoint specific user settings overrides into container to specify default python path,
# virtualenvs from tox to use as python interpreters and pytest settings
COPY .devcontainer/settings.vscode.json /root/.vscode-remote/data/Machine/settings.json

# Make tox workdir ~/.tox by default to don't polute workspace and keep venvs inside container
# using the container filesystem which is faster than working with volumes
RUN echo "alias tox='tox --workdir ~/.tox'" >> ~/.bashrc
