import hashlib

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates

db = SQLAlchemy()


def hash_password(s):
    if isinstance(s, str):
        s = s.encode("utf8")
    return hashlib.sha1(s).hexdigest()


def verify_password(plaintext, ciphertext):
    return hash_password(plaintext) == ciphertext


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True)
    password = db.Column(db.String(128))

    @validates("password")
    def validate_password(self, key, plaintext):
        return hash_password(str(plaintext))
