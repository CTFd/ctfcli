FROM python:3.7-alpine
RUN apk update && \
    apk add \
        python \
        python-dev \
        linux-headers \
        libffi-dev \
        gcc \
        make \
        musl-dev \
        py-pip \
        mysql-client \
        git \
        openssl-dev
RUN adduser -D -u 1001 -s /bin/bash app

WORKDIR /opt/app
RUN mkdir -p /opt/app

COPY src/ /opt/app/

RUN pip install -r requirements.txt

USER 1001
EXPOSE 8000
ENTRYPOINT ["/opt/app/serve.sh"]