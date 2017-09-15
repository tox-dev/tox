#!/usr/bin/env bash

set -e

devpiUsername=${TOX_RELEASE_DEVPI_USERNAME:-obestwalter}
pypiUsername=${TOX_RELEASE_PYPI_USERNAME:-obestwalter}
remote=${TOX_RELEASE_REMOTE:-upstream}


dispatch () {
    if [ -z "$1" ]; then
        echo "usage: $0 prepare->test->publish [version]"
        exit 1
    fi
    if [ "$1" == "prepare" ]; then
        if [ -z "$2" ]; then
            echo "usage: $0 prepare [version]"
            exit 1
        fi
        prepare-release $2
        build-package
    elif [ "$1" == "test" ]; then
         devpi-upload
         trigger-cloud-test $2
    elif [ "$1" == "publish" ]; then
        publish $2
    elif [ "$1" == "undo" ]; then
        undo-prepare-release
    else
        echo "dunno what to do with <<$1>>"
    fi
}

prepare-release () {
    pip install git+git://github.com/avira/towncrier.git@add-pr-links
    python3.6 contrib/towncrier-pre-process.py
    towncrier --draft | most
    tox --version
    echo "consolidate?"
    confirm
    towncrier --yes --version $1
    git add CHANGELOG.rst
    git commit -m "towncrier generated changelog"
    git tag $1
}

build-package () {
    rm dist/tox*
    python setup.py sdist bdist_wheel
}

devpi-upload () {
    if [ ! -d dist ]; then
        echo "needs builds in dist. Build first."
        exit 1
    fi
    echo "loggging in to devpi $devpiUsernames"
    devpi login ${devpiUsername}
    devpi use https://devpi.net/${devpiUsername}/dev
    echo "upload to devpi: $(ls dist/*)"
    confirm
    devpi upload dist/*
}

trigger-cloud-test () {
    cloudTestPath=../devpi-cloud-test-tox
    tag=get-current-tag
    if [ ! -d "$cloudTestPath" ]; then
        echo "needs $cloudTestPath"
        exit 1
    fi
    echo "trigger devpi cloud tests for $tag?"
    confirm
    cd ${cloudTestPath}
    dct trigger $1
    xdg-open https://github.com/obestwalter/devpi-cloud-test-tox
    cd ../tox
}

publish () {
    echo -n "publish "
    echo "upload to devpi: $(ls dist/*)"
    confirm
    twine upload dist/tox-$1-py2.py3-none-any.whl dist/tox-$1.tar.gz
    git push ${remote} master
    git push ${remote} --tags
}

undo-prepare-release () {
    lastTag=$(git describe --abbrev=0 --tags)
    echo "reset ${lastTag}?"
    confirm
    git tag -d ${lastTag}
    git status
    echo "stashing those changes away ..."
    git stash
    rm dist/tox*
}

get-current-tag () {
    echo $(git describe --abbrev=0 --tags)
}

confirm () {
    select confirmation in yes no; do
        if [ ${confirmation} == "no" ]; then
            exit 1
        else
            break
        fi
    done
}

dispatch $1 $2
