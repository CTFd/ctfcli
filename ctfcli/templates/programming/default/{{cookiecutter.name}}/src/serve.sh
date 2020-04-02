#!/bin/sh
socat \
    -T{{cookiecutter.timeout}} \
    TCP-LISTEN:{{cookiecutter.port}},reuseaddr,fork \
    EXEC:"timeout {{cookiecutter.timeout}} ./server.py"