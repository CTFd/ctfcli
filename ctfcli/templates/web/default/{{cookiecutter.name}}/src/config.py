import os


class Config(object):
    SECRET_KEY = os.urandom(32)
    BOOTSTRAP_SERVE_LOCAL = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
