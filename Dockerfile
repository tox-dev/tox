FROM python:3.6
ARG TOX_VERSION=3.2.1
ENV TOX_VERSION=${TOX_VERSION}
RUN apt-get install -y python-dev && \
    pip3 install tox==${TOX_VERSION}
VOLUME /tox
WORKDIR /tox
ENTRYPOINT ["tox"]
