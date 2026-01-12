from flask import Flask, redirect, render_template, request, url_for
from dotenv import load_dotenv
import os
import git 
import hmac
import hashlib
from db import db_read, db_write
from auth import login_manager, authenticate, register_user
from flask_login import login_user, logout_user, login_required, current_user
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Load .env variables
load_dotenv()
W_SECRET = os.getenv("W_SECRET")

# Init flask app
app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = "supersecret"

# Init auth
login_manager.init_app(app)
login_manager.login_view = "login"

# DON'T CHANGE
def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

# DON'T CHANGE
@app.post('/update_server')
def webhook():
    x_hub_signature = request.headers.get('X-Hub-Signature')
    if is_valid_signature(x_hub_signature, request.data, W_SECRET):
        repo = git.Repo('./mysite')
        origin = repo.remotes.origin
        origin.pull()
        return 'Updated PythonAnywhere successfully', 200
    return 'Unathorized', 401

# Auth routes
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user = authenticate(
            request.form["username"],
            request.form["password"]
        )

        if user:
            login_user(user)
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for("index"))

        error = "Benutzername oder Passwort ist falsch."

    return render_template(
        "auth.html",
        title="In dein Konto einloggen",
        action=url_for("login"),
        button_label="Einloggen",
        error=error,
        footer_text="Noch kein Konto?",
        footer_link_url=url_for("register"),
        footer_link_label="Registrieren"
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        ok = register_user(username, password)
        if ok:
            return redirect(url_for("login"))

        error = "Benutzername existiert bereits."

    return render_template(
        "auth.html",
        title="Neues Konto erstellen",
        action=url_for("register"),
        button_label="Registrieren",
        error=error,
        footer_text="Du hast bereits ein Konto?",
        footer_link_url=url_for("login"),
        footer_link_label="Einloggen"
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))



# App routes
@app.route("/", methods=["GET"])
@login_required
def index():
    # GET: search
    q = request.args.get("q", "")
    t = request.args.get("t", "club")
    results = []
    if q:
        if t == "player":
            results = db_read("SELECT players.id, players.name, players.position, clubs.name AS club FROM players LEFT JOIN clubs ON players.club_id = clubs.id WHERE players.name LIKE %s AND clubs.competition_id = %s", (f"%{q}%", 2021))
        elif t == "trainer":
            results = db_read("SELECT trainers.id, trainers.name, clubs.name AS club FROM trainers LEFT JOIN clubs ON trainers.club_id = clubs.id WHERE trainers.name LIKE %s AND clubs.competition_id = %s", (f"%{q}%", 2021))
        elif t == "title":
            results = db_read("SELECT titles.id, titles.title, titles.year, clubs.name AS club FROM titles LEFT JOIN clubs ON titles.club_id = clubs.id WHERE titles.title LIKE %s AND clubs.competition_id = %s", (f"%{q}%", 2021))
        else:
            results = db_read("SELECT id, name, country, stadium FROM clubs WHERE name LIKE %s AND competition_id = %s", (f"%{q}%", 2021))
    return render_template("main_page.html", results=results, query=q, type=t)


@app.route("/users", methods=["GET"])
@login_required
def users():
    pass

if __name__ == "__main__":
    app.run()
