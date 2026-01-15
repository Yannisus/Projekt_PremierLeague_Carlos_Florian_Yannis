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

# ============ SEARCH ROUTES ============

@app.route("/", methods=["GET"])
@login_required
def index():
    q = request.args.get("q", "")
    t = request.args.get("t", "club")
    results = []
    
    if q:
        if t == "player":
            results = db_read(
                "SELECT players.id, players.name, players.position, players.club_id, clubs.name AS club FROM players LEFT JOIN clubs ON players.club_id = clubs.id WHERE players.name LIKE %s",
                (f"%{q}%",)
            )
        elif t == "trainer":
            results = db_read(
                "SELECT trainers.id, trainers.name, trainers.club_id, clubs.name AS club FROM trainers LEFT JOIN clubs ON trainers.club_id = clubs.id WHERE trainers.name LIKE %s",
                (f"%{q}%",)
            )
        elif t == "title":
            results = db_read(
                "SELECT titles.id, titles.title, titles.year, titles.club_id, clubs.name AS club FROM titles LEFT JOIN clubs ON titles.club_id = clubs.id WHERE titles.title LIKE %s",
                (f"%{q}%",)
            )
        else:  # club
            results = db_read(
                "SELECT id, name, country, stadium FROM clubs WHERE name LIKE %s",
                (f"%{q}%",)
            )
    
    return render_template("main_page.html", results=results, query=q, type=t)

@app.route('/club/<int:club_id>')
@login_required
def club(club_id):
    club = db_read(
        "SELECT id, name, country, stadium FROM clubs WHERE id = %s",
        (club_id,),
        single=True
    )
    if not club:
        return redirect(url_for('index'))
    
    players = db_read("SELECT id, name, position FROM players WHERE club_id = %s", (club_id,))
    trainers = db_read("SELECT id, name FROM trainers WHERE club_id = %s", (club_id,))
    titles = db_read("SELECT id, title, year FROM titles WHERE club_id = %s ORDER BY year DESC", (club_id,))
    
    return render_template('club.html', club=club, players=players, trainers=trainers, titles=titles)

@app.route("/manage", methods=["GET"])
@login_required
def manage():
    clubs = db_read("SELECT id, name, country, stadium FROM clubs")
    return render_template("manage.html", clubs=clubs or [])

# ============ CLUB ROUTES ============

@app.route("/club/new", methods=["GET", "POST"])
@login_required
def new_club():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        stadium = request.form.get("stadium", "").strip()
        
        if not name:
            error = "Club-Name ist erforderlich"
        else:
            try:
                db_write(
                    "INSERT INTO clubs (name, country, stadium) VALUES (%s, %s, %s)",
                    (name, country or None, stadium or None)
                )
                return redirect(url_for("manage"))
            except Exception as e:
                logging.error(f"Error creating club: {str(e)}", exc_info=True)
                error = f"Fehler: {str(e)}"
    
    return render_template("new_club.html", error=error)

# ============ PLAYER ROUTES ============

@app.route("/player/new", methods=["GET", "POST"])
@login_required
def new_player():
    clubs = db_read("SELECT id, name FROM clubs") or []
    error = None
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        position = request.form.get("position", "").strip()
        club_id = request.form.get("club_id", "").strip()
        
        if not name or not club_id:
            error = "Name und Club sind erforderlich"
        else:
            try:
                db_write(
                    "INSERT INTO players (name, position, club_id) VALUES (%s, %s, %s)",
                    (name, position or None, club_id)
                )
                return redirect(url_for("manage"))
            except Exception as e:
                logging.error(f"Error creating player: {str(e)}", exc_info=True)
                error = f"Fehler: {str(e)}"
    
    return render_template("new_player.html", clubs=clubs, error=error)

# ============ TRAINER ROUTES ============

@app.route("/trainer/new", methods=["GET", "POST"])
@login_required
def new_trainer():
    clubs = db_read("SELECT id, name FROM clubs") or []
    error = None
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        club_id = request.form.get("club_id", "").strip()
        
        if not name or not club_id:
            error = "Name und Club sind erforderlich"
        else:
            try:
                db_write(
                    "INSERT INTO trainers (name, club_id) VALUES (%s, %s)",
                    (name, club_id)
                )
                return redirect(url_for("manage"))
            except Exception as e:
                logging.error(f"Error creating trainer: {str(e)}", exc_info=True)
                error = f"Fehler: {str(e)}"
    
    return render_template("new_trainer.html", clubs=clubs, error=error)

# ============ TITLE ROUTES ============

@app.route("/title/new", methods=["GET", "POST"])
@login_required
def new_title():
    clubs = db_read("SELECT id, name FROM clubs") or []
    error = None
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        year = request.form.get("year", "").strip()
        club_id = request.form.get("club_id", "").strip()
        
        if not title or not year or not club_id:
            error = "Titel, Jahr und Club sind erforderlich"
        else:
            try:
                db_write(
                    "INSERT INTO titles (title, year, club_id) VALUES (%s, %s, %s)",
                    (title, year, club_id)
                )
                return redirect(url_for("manage"))
            except Exception as e:
                logging.error(f"Error creating title: {str(e)}", exc_info=True)
                error = f"Fehler: {str(e)}"
    
    return render_template("new_title.html", clubs=clubs, error=error)

@app.route("/users", methods=["GET"])
@login_required
def users():
    pass

if __name__ == "__main__":
    app.run()
