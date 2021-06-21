FROM python:3.7-slim-buster

RUN apt-get update -y \
    && apt-get install --no-install-recommends -y socat \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir "/opt/{{cookiecutter.name}}"
COPY ./src/* "/opt/{{cookiecutter.name}}/"
RUN pip install -r "/opt/{{cookiecutter.name}}/requirements.txt"
WORKDIR "/opt/{{cookiecutter.name}}/"
RUN chmod +x serve.sh server.py

EXPOSE {{cookiecutter.port}}
CMD ./serve.sh
