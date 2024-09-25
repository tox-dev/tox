# tox

[![PyPI](https://img.shields.io/pypi/v/tox)](https://pypi.org/project/tox/)
[![Supported Python
versions](https://img.shields.io/pypi/pyversions/tox.svg)](https://pypi.org/project/tox/)
[![Downloads](https://static.pepy.tech/badge/tox/month)](https://pepy.tech/project/tox)
[![Documentation
status](https://readthedocs.org/projects/tox/badge/?version=latest)](https://tox.readthedocs.io/en/latest/?badge=latest)
[![check](https://github.com/tox-dev/tox/actions/workflows/check.yaml/badge.svg)](https://github.com/tox-dev/tox/actions/workflows/check.yaml)

# Table of Contents

- [Main Features](#main-features)
- [Benefits of Using tox](#benefits-of-using-tox)
- [Setup and Configuration](#setup-and-configuration)
- [Using Tox in a Real Project](#using-tox-in-a-real-project)
- [How to Contribute](#how-to-contribute)

# Main Features

`tox` aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging, testing
and release process of Python software (alongside [pytest](https://docs.pytest.org/en/latest/) and
[devpi](https://www.devpi.net)).

tox is a generic virtual environment management and test command line tool you can use for:

- checking your package builds and installs correctly under different environments (such as different Python
  implementations, versions or installation dependencies),
- running your tests in each of the environments with the test tool of choice,
- acting as a frontend to continuous integration servers, greatly reducing boilerplate and merging CI and shell-based
  testing.

# Benefits of Using tox

Using tox offers several key benefits for Python developers:

- **Automation**: Tox automates repetitive tasks, such as running tests across multiple environments or packaging your project. This reduces human error and frees up time for developers to focus on building features rather than managing testing environments.

- **Consistency**: By providing isolated virtual environments, tox ensures that tests run consistently regardless of the developer’s local setup. This consistency is crucial for ensuring that the tests you run locally will behave the same way in CI or on another developer's machine.

- **Cross-Platform Support**: Tox works across major operating systems (Linux, macOS, and Windows), making it a versatile tool for teams working in diverse development environments.

- **Reduced CI Boilerplate**: By configuring your testing and linting in tox, you can reduce the amount of boilerplate needed for continuous integration pipelines. Instead of duplicating configuration files for each CI tool, you can configure tox once and reuse it across multiple platforms.

- **Flexible Configuration**: Tox’s configuration system allows for flexible and customizable setups. Whether you're running a single test suite or managing multiple testing configurations, tox can handle various use cases with ease.

# Setup and Configuration

To start using tox in your Python project, follow these steps for a clearer setup:

1. **Install Tox**:
   Tox is a Python tool that can be installed via the Python package manager. After installation, tox allows you to create isolated virtual environments for your project and run your tests in them.

2. **Create a Configuration File**:
   After installing tox, a configuration file (`tox.ini`) is required to define the environments in which your tests will run. In this file, you specify which Python versions to test against and what testing tools (e.g., `pytest`) or dependencies will be used in each environment.

3. **Running Tox**:
   After setting up the configuration, you can run tox by executing a single command. Tox will automatically create virtual environments for each environment specified in the configuration and run your tests within those environments.

4. **Customizing Your Environments**:
   Tox allows you to customize each environment’s dependencies and commands. For instance, you can set up environments to handle different Python versions or configurations for linting and testing. You can also specify additional tasks like running linters or formatting tools as part of the testing process.

5. **Configuring Additional Options**:
   Tox’s configuration options include setting the Python versions to test, specifying dependencies to be installed in each environment, and defining commands that should run during testing. These options make tox adaptable for various project needs, ensuring that it fits into a wide range of development workflows.

# Using Tox in a Real Project

Tox is commonly used in Python projects to automate testing across multiple Python versions. Here’s an overview of how it can be applied:

1. **Project Setup**:
   In a typical Python project, you would have a directory structure that includes source code, a testing framework, and a configuration file for tox.

2. **Tox Configuration**:
   The configuration file tells tox which Python versions to test against, which dependencies to install, and what commands to run. This file is flexible and allows you to define multiple environments tailored to different tasks, such as running tests, checking code style, or building the project.

3. **Running Tests Across Versions**:
   Once configured, running tox automates the process of testing your project in different environments. Tox will create virtual environments for each specified Python version, install the necessary dependencies, and run the tests. This ensures that your project is compatible across the Python versions you support.

Please read our [user guide](https://tox.wiki/en/latest/user_guide.html#basic-example) for a visual, in-depth example and even more detailed
introduction, or watch [this YouTube video](https://www.youtube.com/watch?v=SFqna5ilqig) that presents the problem space
and how tox solves it.

# How to Contribute

We welcome contributions from the community, whether it’s fixing bugs, adding new features, or improving documentation. Here’s how you can get started:

1. **Fork the Repository**:
   If you’d like to contribute, start by forking the tox repository to your GitHub account. This allows you to make changes independently of the main project.

2. **Clone and Create a Branch**:
   Once you’ve forked the repository, clone it to your local machine. Create a new branch for each feature or fix you’re working on to keep your contributions organized.

3. **Submit a Pull Request**:
   After you’ve made your changes, submit a pull request (PR) to the main repository. Be sure to provide a clear explanation of the changes you made, the issue you’re addressing, or the feature you’re adding. Make sure your contribution aligns with the project’s style and standards.

4. **Documentation Contributions**:
   If your contribution involves changes to how tox is used (e.g., new configuration options or features), make sure to update the documentation accordingly. This helps other users understand how to work with new features and keeps the documentation up to date.

For more detailed contribution guidelines, please refer to our [Contributing Guide](https://github.com/tox-dev/tox/blob/main/CONTRIBUTING.md) (when created).
