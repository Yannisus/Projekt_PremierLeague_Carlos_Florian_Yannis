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
import requests

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Load .env variables
load_dotenv()
W_SECRET = os.getenv("W_SECRET")
API_KEY = os.getenv("FOOTBALL_API_KEY", "c8d4f0a982ae42269ea20d8f123a048e")
API_BASE = os.getenv("FOOTBALL_API_BASE", "https://api.football-data.org/v4")
API_HEADERS = {"X-Auth-Token": API_KEY} if API_KEY else {}
COMPETITION_ID = "PL"

logging.info(f"API_KEY set: {bool(API_KEY)}")
logging.info(f"API_BASE: {API_BASE}")

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
def search_clubs_api(query):
    """Search clubs from API v4"""
    try:
        url = f"{API_BASE}/competitions/{COMPETITION_ID}/teams"
        logging.info(f"Fetching clubs from: {url}")
        resp = requests.get(url, headers=API_HEADERS, timeout=10)
        resp.raise_for_status()
        teams = resp.json().get("teams", [])
        results = []
        for team in teams:
            if query.lower() in team.get("name", "").lower():
                results.append({
                    "id": team.get("id"),
                    "name": team.get("name"),
                    "country": team.get("area", {}).get("name"),
                    "stadium": team.get("venue"),
                    "competition_name": "Premier League"
                })
        logging.info(f"Found {len(results)} clubs for query: {query}")
        return results
    except Exception as e:
        logging.error(f"API search error: {str(e)}", exc_info=True)
        return []

def search_players_api(query):
    """Search players from API v4"""
    try:
        url = f"{API_BASE}/competitions/{COMPETITION_ID}/teams"
        logging.info(f"Fetching teams from: {url}")
        resp = requests.get(url, headers=API_HEADERS, timeout=10)
        resp.raise_for_status()
        teams = resp.json().get("teams", [])
        results = []
        
        for team in teams:
            try:
                team_id = team.get("id")
                team_name = team.get("name")
                # Squad is included in the team response in v4
                squad = team.get("squad", [])
                
                for member in squad:
                    if query.lower() in member.get("name", "").lower():
                        results.append({
                            "id": member.get("id"),
                            "name": member.get("name"),
                            "position": member.get("position"),
                            "club_id": team_id,
                            "club": team_name
                        })
            except Exception as e:
                logging.warning(f"Error processing team {team_id}: {str(e)}")
                continue
        
        logging.info(f"Found {len(results)} players for query: {query}")
        return results
    except Exception as e:
        logging.error(f"API search error: {str(e)}", exc_info=True)
        return []

def search_trainers_api(query):
    """Search trainers from API v4 - v4 free tier doesn't easily provide coach data"""
    # In v4, coaches/trainers are not included in the free tier squad data
    # Return empty list
    logging.info("Trainer search not available in v4 free tier")
    return []

@app.route("/", methods=["GET"])
@login_required
def index():
    # GET: search
    q = request.args.get("q", "")
    t = request.args.get("t", "club")
    results = []
    if q:
        if t == "player":
            results = search_players_api(q)
        elif t == "trainer":
            results = search_trainers_api(q)
        else:
            results = search_clubs_api(q)
    return render_template("main_page.html", results=results, query=q, type=t)



# === Lokales Caching für Clubdaten ===
@app.route('/club/<int:club_id>')
@login_required
def club(club_id):
    try:
        # Zuerst versuchen, Clubdaten aus der lokalen DB zu lesen
        club_row = db_read("SELECT * FROM clubs WHERE id=%s", (club_id,), single=True)
        if club_row:
            club = {
                "id": club_row.get("id"),
                "name": club_row.get("name") or club_row.get("club_name"),
                "country": club_row.get("country"),
                "stadium": club_row.get("stadium"),
                "competition_name": club_row.get("competition_name"),
                "trainer": club_row.get("trainer"),
                "title": club_row.get("title")
            }
            # Spieler aus players_by_club holen
            players = db_read("""
                SELECT p.id, p.player_name as name, NULL as position
                FROM players_by_club pb
                JOIN players p ON pb.player_id = p.id
                WHERE pb.club_id = %s
            """, (club_id,))
        else:
            # Wenn nicht vorhanden, von der API holen und in DB speichern
            url = f"{API_BASE}/competitions/{COMPETITION_ID}/teams"
            resp = requests.get(url, headers=API_HEADERS, timeout=10)
            resp.raise_for_status()
            teams = resp.json().get("teams", [])
            club_data = next((team for team in teams if team.get("id") == club_id), None)
            if not club_data:
                return redirect(url_for('index'))
            # In DB speichern
            db_write("INSERT INTO clubs (id, name, country, stadium, competition_id, competition_name) VALUES (%s, %s, %s, %s, %s, %s)",
                (club_data.get("id"), club_data.get("name"), club_data.get("area", {}).get("name"), club_data.get("venue"), COMPETITION_ID, "Premier League"))
            club = {
                "id": club_data.get("id"),
                "name": club_data.get("name"),
                "country": club_data.get("area", {}).get("name"),
                "stadium": club_data.get("venue"),
                "competition_name": "Premier League",
                "trainer": None,
                "title": None
            }
            players = []
            squad = club_data.get("squad", [])
            for member in squad:
                if member.get("position"):
                    players.append({
                        "id": member.get("id"),
                        "name": member.get("name"),
                        "position": member.get("position")
                    })
        # Trainer und Titel aus DB holen
        trainers = db_read("""
            SELECT c.coach_firstname, c.coach_name, cp.start_year, cp.end_year
            FROM coaches_per_club cp
            JOIN coaches c ON cp.coach_id = c.id
            WHERE cp.club_id = %s
        """, (club_id,))
        titles = db_read("""
            SELECT t.title_name, tp.year_
            FROM titles_per_club tp
            JOIN titles t ON tp.title_id = t.id
            WHERE tp.club_id = %s
        """, (club_id,))
        return render_template('club.html', club=club, players=players, trainers=trainers, titles=titles)
    except Exception as e:
        logging.error(f"Error fetching club {club_id}: {str(e)}", exc_info=True)
        return redirect(url_for('index'))

@app.route("/users", methods=["GET"])
@login_required
def users():
    pass

# === Trainer manuell hinzufügen ===
@app.route("/add_trainer", methods=["GET", "POST"])
@login_required
def add_trainer():
    if request.method == "POST":
        coach_firstname = request.form["coach_firstname"]
        coach_name = request.form["coach_name"]
        club_name = request.form["club_name"]
        start_year = request.form.get("start_year")
        end_year = request.form.get("end_year")
        # Club anlegen, falls nicht vorhanden (API holen, falls nötig)
        club = db_read("SELECT id FROM clubs WHERE club_name=%s", (club_name,))
        if club and len(club) > 0 and club[0]:
            club_id = club[0][0] if isinstance(club[0], (list, tuple)) else club[0].get("id")
        # Versuche Clubdaten von der API zu holen und einzufügen, falls nicht gefunden
        else:
            try:
                import requests
                url = f"{API_BASE}/competitions/{COMPETITION_ID}/teams"
                resp = requests.get(url, headers=API_HEADERS, timeout=10)
                resp.raise_for_status()
                teams = resp.json().get("teams", [])
                team = next((t for t in teams if t.get("name", "").lower() == club_name.lower()), None)
                if team:
                    db_write("INSERT INTO clubs (name, country, stadium, competition_id, competition_name) VALUES (%s, %s, %s, %s, %s)",
                        (team.get("name"), team.get("area", {}).get("name"), team.get("venue"), COMPETITION_ID, "Premier League"))
                    club_id = db_read("SELECT id FROM clubs WHERE name=%s ORDER BY id DESC LIMIT 1", (team.get("name"),))[0][0]
                else:
                    # Fallback: nur Name eintragen
                    db_write("INSERT INTO clubs (club_name) VALUES (%s)", (club_name,))
                    club_id = db_read("SELECT id FROM clubs WHERE club_name=%s ORDER BY id DESC LIMIT 1", (club_name,))[0][0]
            except Exception as e:
                print("Fehler beim API-Club-Insert:", e)
                db_write("INSERT INTO clubs (club_name) VALUES (%s)", (club_name,))
                club_id = db_read("SELECT id FROM clubs WHERE club_name=%s ORDER BY id DESC LIMIT 1", (club_name,))[0][0]
        # Trainer und Titel direkt in clubs Tabelle speichern
        db_write("UPDATE clubs SET trainer=%s WHERE id=%s", (coach_name, club_id))
        # Trainer anlegen
        db_write("INSERT INTO coaches (coach_name, coach_firstname) VALUES (%s, %s)", (coach_name, coach_firstname))
        coach_id = db_read("SELECT id FROM coaches WHERE coach_name=%s AND coach_firstname=%s ORDER BY id DESC LIMIT 1", (coach_name, coach_firstname))[0][0]
        db_write("INSERT INTO coaches_per_club (coach_id, club_id, start_year, end_year) VALUES (%s, %s, %s, %s)", (coach_id, club_id, start_year, end_year))
        flash("Trainer erfolgreich hinzugefügt.")
        # Nach dem Hinzufügen zur Suche weiterleiten und Notify anzeigen
        return redirect(url_for("index", notify="trainer_added"))
    return render_template("add_trainer.html")

# === Titel manuell hinzufügen ===
@app.route("/add_title", methods=["GET", "POST"])
@login_required
def add_title():
    if request.method == "POST":
        title_name = request.form["title_name"]
        club_name = request.form["club_name"]
        year_ = request.form["year_"]
        # Club anlegen, falls nicht vorhanden (API holen, falls nötig)
        club = db_read("SELECT id FROM clubs WHERE club_name=%s", (club_name,))
        if club:
            club_id = club[0][0]
        else:
            try:
                from scripts.fetch_api import fetch_teams, upsert_club
                teams = fetch_teams()
                team = next((t for t in teams if t.get("name", "").lower() == club_name.lower()), None)
                if team:
                    club_id = upsert_club(team)
                else:
                    db_write("INSERT INTO clubs (club_name) VALUES (%s)", (club_name,))
                    club_id = db_read("SELECT id FROM clubs WHERE club_name=%s ORDER BY id DESC LIMIT 1", (club_name,))[0][0]
            except Exception as e:
                print("Fehler beim API-Club-Insert:", e)
                db_write("INSERT INTO clubs (club_name) VALUES (%s)", (club_name,))
                club_id = db_read("SELECT id FROM clubs WHERE club_name=%s ORDER BY id DESC LIMIT 1", (club_name,))[0][0]
        # Titel anlegen
        db_write("INSERT INTO titles (title_name) VALUES (%s)", (title_name,))
        title_id = db_read("SELECT id FROM titles WHERE title_name=%s ORDER BY id DESC LIMIT 1", (title_name,))[0][0]
        db_write("INSERT INTO titles_per_club (year_, title_id, club_id) VALUES (%s, %s, %s)", (year_, title_id, club_id))
        # Titel auch direkt in clubs Tabelle speichern
        db_write("UPDATE clubs SET title=%s WHERE id=%s", (title_name, club_id))
        flash("Titel erfolgreich hinzugefügt.")
        return redirect(url_for("add_title"))
    return render_template("add_title.html")

if __name__ == "__main__":
    app.run()
