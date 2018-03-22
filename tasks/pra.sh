#!/usr/bin/env bash

# Personal Release Assistant (TM)

set -e

if [ -z "$1" ]; then
    echo "workflow: $0 <command> [arg]"
    echo "    prep <version>"
    echo "    upload <devpi username>"
    echo "    test (optional)"
    echo "    release"
    exit 1
fi

if [ -z "$2" ]; then
    # if not passed: take it from tag created in prep
    VERSION=$(git describe --abbrev=0 --tags)
else
    # only the prep step needs the version
    VERSION=$2
fi

dispatch () {
    if [ "$1" == "prep" ]; then
        if [ -z "$2" ]; then
            echo "usage: $0 prep <version>"
            exit 1
        fi
        prep
    elif [ "$1" == "upload" ]; then
        devpi_upload $2
    elif [ "$1" == "test" ]; then
        devpi_cloud_test
    elif [ "$1" == "release" ]; then
        pypi_release
    else
        exit 1
    fi
}

prep () {
    python3.6 tasks/pre-process-changelog.py
    towncrier --draft --version ${VERSION}
    towncrier --yes --version ${VERSION}
    pip install -U readme-renderer
    python setup.py check -r -s
    git add CHANGELOG.rst
    git status
    _confirm "commit changelog and tag repo as ${VERSION}?"
    git commit -m "release preparation for ${VERSION}" || true
    git tag -s ${VERSION} -m "release tox ${VERSION}" || true
    rm dist/tox* || true
    python setup.py sdist bdist_wheel
    pip install -U dist/tox-${VERSION}.tar.gz
    tox --version
    _confirm "package and version o.k.?"
}

devpi_upload () {
    if [ ! -d dist ]; then
        echo "needs builds in dist. Build first."
        exit 1
    fi
    echo "loggging in to devpi $1"
    devpi use https://m.devpi.net/$1/dev
    devpi login $1
    _confirm "upload to devpi: $(ls dist/*)?"
    devpi upload dist/*
}

devpi_cloud_test () {
    dctPath=../devpi-cloud-test
    cloudTestPath=../devpi-cloud-test-tox
    if [ ! -d "$cloudTestPath" ]; then
        echo "needs $cloudTestPath"
        exit 1
    fi
    pip install -e ${dctPath}
    _confirm "trigger devpi cloud tests for ${VERSION}?"
    cd ${cloudTestPath}
    dct trigger ${VERSION}
    xdg-open https://github.com/tox-dev/devpi-cloud-test-tox
    cd ../tox
}

pypi_release () {
    PACKAGES=$(ls dist/*)
    _confirm "upload to pypi: $PACKAGES?"
    # TODO get devpi push to work again
    # get rid of this ...
    twine upload ${PACKAGES}
    # ... and do this when this is fixed:
    # https://github.com/devpi/devpi/issues/449
    # devpi push tox==${VERSION} pypi:pypi

    # TODO do the right thing here when using a release branch
    # promote changes in code and tag to repo
    # git push upstream master
    # git push upstream ${VERSION}
}

_confirm () {
    echo "please confirm: $1"
    select confirmation in yes no; do
        if [ ${confirmation} == "no" ]; then
            exit 1
        else
            break
        fi
    done
}

dispatch $1 $2
