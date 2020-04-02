FROM python:3.7-alpine

RUN apk update && \
    apk add \
        socat
RUN mkdir "/opt/{{cookiecutter.name}}"
COPY ./src/* "/opt/{{cookiecutter.name}}/"
RUN pip install -r "/opt/{{cookiecutter.name}}/requirements.txt"

EXPOSE {{cookiecutter.port}}
WORKDIR "/opt/{{cookiecutter.name}}/"
CMD ./serve.sh
