#!/usr/bin/env bash

set -e

devpiUsername=${TOX_RELEASE_DEVPI_USERNAME:-obestwalter}
pypiUsername=${TOX_RELEASE_PYPI_USERNAME:-obestwalter}
remote=${TOX_RELEASE_REMOTE:-upstream}


dispatch () {
    if [ -z "$1" ]; then
        echo "usage: $0 command [version]"
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
    pip install -U "git+git://github.com/avira/towncrier.git@tox"
    python3.6 contrib/towncrier-pre-process.py
    towncrier --draft --version $1 | most
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
    ls dist
}

devpi-upload () {
    devpi login ${devpiUsername}
    devpi use https://devpi.net/${devpiUsername}/dev
    devpi upload dist/tox-$1-py2.py3-none-any.whl dist/tox-$1.tar.gz
}

trigger-cloud-test () {
    cd ../devpi-cloud-test-tox
    dct trigger $1
    xdg-open https://github.com/obestwalter/devpi-cloud-test-tox
    cd ../tox
}

publish () {
    echo -n "publish from dist?"
    confirm
    git push ${remote} master
    twine upload upload dist/tox-$1-py2.py3-none-any.whl dist/tox-$1.tar.gz
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
