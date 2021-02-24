#!/usr/bin/env python
import functools

from flask import Flask, redirect, render_template, request, session, url_for
from flask_bootstrap import Bootstrap
from sqlalchemy.exc import IntegrityError

from models import Users, db, hash_password, verify_password

app = Flask(__name__)
app.config.from_object("config.Config")
bootstrap = Bootstrap(app)

db.init_app(app)
with app.app_context():
    db.create_all()


def authed():
    user_id = session.get("id", None)
    return user_id is not None


def authed_only(f):
    @functools.wraps(f)
    def _authed_only(*args, **kwargs):
        if authed():
            return f(*args, **kwargs)
        else:
            return redirect(url_for("login", next=request.full_path))

    return _authed_only


@app.context_processor
def inject_user():
    if session:
        return dict(session)
    return dict()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/profile")
def profile():
    user = Users.query.filter_by(id=session["id"]).first()
    return render_template("profile.html", user=user)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"].strip()
        errors = []

        user = Users.query.filter_by(username=username).first()
        if user:
            pass_test = verify_password(plaintext=password, ciphertext=user.password)
            if pass_test is False:
                errors.append("Incorrect password")
        else:
            errors.append("User does not exist")
            return render_template("login.html", errors=errors)

        if errors:
            return render_template("login.html", errors=errors)

        session["id"] = user.id
        session["username"] = user.username

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            user = Users(username=username, password=password)
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            return render_template(
                "register.html", errors=["That username is already taken"]
            )

        session["id"] = user.id
        return redirect("/")

    return render_template("register.html")


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
