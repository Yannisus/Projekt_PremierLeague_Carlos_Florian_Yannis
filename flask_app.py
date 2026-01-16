from flask import Flask, redirect, render_template, request, url_for, flash
import os
try:
    from db import db_read, db_write, USE_SQLITE
except ImportError:
    from db import db_read, db_write
    USE_SQLITE = True # Fallback assumption

from auth import login_manager, authenticate, register_user
from flask_login import login_user, logout_user, login_required, current_user
import logging
import uuid

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Init flask app
app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = "supersecret_local_key"

# Init auth
login_manager.init_app(app)
login_manager.login_view = "login"

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = authenticate(request.form["username"], request.form["password"])
        if user:
            login_user(user)
            return redirect(url_for("index"))
        error = "Benutzername oder Passwort ist falsch."
    return render_template("auth.html", title="Einloggen", action=url_for("login"), button_label="Einloggen", error=error, footer_text="Noch kein Konto?", footer_link_url=url_for("register"), footer_link_label="Registrieren")

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        if register_user(request.form["username"], request.form["password"]):
            return redirect(url_for("login"))
        error = "Benutzername existiert bereits."
    return render_template("auth.html", title="Neues Konto", action=url_for("register"), button_label="Registrieren", error=error, footer_text="Du hast bereits ein Konto?", footer_link_url=url_for("login"), footer_link_label="Einloggen")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# === MAIN LIST / SEARCH ===
@app.route("/", methods=["GET"])
@login_required
def index():
    q = request.args.get("q", "").strip()
    t = request.args.get("t", "club")
    
    # Statistics for Dashboard
    def get_count(table):
        try:
            res = db_read(f"SELECT COUNT(*) as c FROM {table}", single=True)
            return res['c'] if res else 0
        except:
            return 0

    stats = {
        "clubs": get_count("clubs"),
        "players": get_count("players"),
        "trainers": get_count("coaches"),
        "titles": get_count("titles")
    }
    
    if USE_SQLITE:
        # Only flash once per session ideally, but for now just show it if it's confusing the user
        # check if it's already flashed? No, just add it.
        # But flash persists until read. If we refresh, it might stack.
        # Let's just rely on the user seeing it once.
        pass 
        # Actually, let's not spam the flash message. The Dashboard text is better.

    results = []

    if not q:
        # Show all clubs sorted alphabetically
        clubs = db_read("SELECT * FROM clubs ORDER BY club_name ASC")
        for c in clubs:
            results.append({
                "id": c.get("id"),
                "name": c.get("club_name") or c.get("name"),
                "country": c.get("country"),
                "details": f"{c.get('country', '')}",
                "link": url_for('club', club_id=c.get("id"))
            })
    else:
        search_term = f"%{q}%"
        if t == "club":
            filtered = db_read("SELECT * FROM clubs WHERE club_name LIKE %s OR country LIKE %s ORDER BY club_name ASC", (search_term, search_term))
            for c in filtered:
                results.append({
                    "id": c.get("id"),
                    "name": c.get("club_name"),
                    "details": c.get("country"),
                    "link": url_for('club', club_id=c.get("id"))
                })
        elif t == "player":
            players = db_read("""
                SELECT p.id, p.player_firstname, p.player_name, c.club_name, c.id as club_id 
                FROM players p 
                JOIN players_by_club pc ON p.id = pc.player_id 
                JOIN clubs c ON pc.club_id = c.id
                WHERE p.player_name LIKE %s OR p.player_firstname LIKE %s
            """, (search_term, search_term))
            for p in players:
                results.append({
                    "id": p.get("club_id"), # Link to club page
                    "name": f"{p.get('player_firstname')} {p.get('player_name')}",
                    "details": f"Spieler bei {p.get('club_name')}",
                    "link": url_for('club', club_id=p.get('club_id'))
                })
        elif t == "trainer":
            coaches = db_read("""
                SELECT c.id, c.coach_firstname, c.coach_name, cl.club_name, cl.id as club_id
                FROM coaches c
                JOIN coaches_per_club cc ON c.id = cc.coach_id
                JOIN clubs cl ON cc.club_id = cl.id
                WHERE c.coach_name LIKE %s OR c.coach_firstname LIKE %s
            """, (search_term, search_term))
            for c in coaches:
                results.append({
                    "id": c.get("club_id"),
                    "name": f"{c.get('coach_firstname')} {c.get('coach_name')}",
                    "details": f"Trainer bei {c.get('club_name')}",
                    "link": url_for('club', club_id=c.get('club_id'))
                })
        elif t == "title":
            titles = db_read("""
                SELECT t.title_name, tp.year_, c.club_name, c.id as club_id
                FROM titles t
                JOIN titles_per_club tp ON t.id = tp.title_id
                JOIN clubs c ON tp.club_id = c.id
                WHERE t.title_name LIKE %s
            """, (search_term,))
            for ti in titles:
                results.append({
                    "id": ti.get("club_id"),
                    "name": ti.get("title_name"),
                    "details": f"{ti.get('year_')} - {ti.get('club_name')}",
                    "link": url_for('club', club_id=ti.get('club_id'))
                })

    return render_template("main_page.html", results=results, query=q, type=t, stats=stats, use_sqlite=USE_SQLITE)

# === CLUB DETAILS ===
@app.route('/club/<int:club_id>')
@login_required
def club(club_id):
    club = db_read("SELECT * FROM clubs WHERE id=%s", (club_id,), single=True)
    if not club:
        return render_template('club.html', notfound=True)
    
    # Ensure display name is preferably 'club_name' which we use effectively
    if not club.get('club_name') and club.get('name'):
        club['club_name'] = club['name']

    players = db_read("""
        SELECT p.player_firstname, p.player_name 
        FROM players p 
        JOIN players_by_club pc ON p.id = pc.player_id 
        WHERE pc.club_id = %s
    """, (club_id,))

    trainers = db_read("""
        SELECT c.coach_firstname, c.coach_name, cc.start_year, cc.end_year
        FROM coaches c
        JOIN coaches_per_club cc ON c.id = cc.coach_id
        WHERE cc.club_id = %s
    """, (club_id,))

    titles = db_read("""
        SELECT t.title_name, tp.year_
        FROM titles t
        JOIN titles_per_club tp ON t.id = tp.title_id
        WHERE tp.club_id = %s ORDER BY tp.year_ DESC
    """, (club_id,))

    return render_template('club.html', club=club, players=players, trainers=trainers, titles=titles)

# === CREATE ROUTES ===
@app.route("/add_club", methods=["GET", "POST"])
@login_required
def add_club():
    if request.method == "POST":
        name = request.form["club_name"]
        country = request.form["country"]
        stadium = request.form["stadium"]
        u_id = str(uuid.uuid4())
        
        try:
            db_write("INSERT INTO clubs (club_name, country, stadium, uuid) VALUES (%s, %s, %s, %s)", (name, country, stadium, u_id))
            
            # Retrieve the ID of the newly created club to redirect to it
            new_club = db_read("SELECT id FROM clubs WHERE uuid=%s", (u_id,), single=True)
            if new_club and new_club.get("id"):
                flash(f"Club '{name}' erfolgreich erstellt!", "success")
                return redirect(url_for('club', club_id=new_club.get("id")))
            
            flash(f"Club '{name}' erstellt, aber Detailseite nicht gefunden.", "warning")
        except Exception as e:
            flash(f"Fehler beim Erstellen: {e}", "danger")
            logging.error("Create club error: %s", e)
            
        return redirect(url_for('index'))
    return render_template("add_club.html")

@app.route("/add_player", methods=["GET", "POST"])
@login_required
def add_player():
    if request.method == "POST":
        first = request.form["player_firstname"]
        last = request.form["player_name"]
        club_id = request.form["club_id"]
        
        db_write("INSERT INTO players (player_firstname, player_name, player_identifier) VALUES (%s, %s, %s)", (first, last, f"{first}_{last}".lower()))
        player_row = db_read("SELECT id FROM players ORDER BY id DESC LIMIT 1", single=True)
        player_id = player_row['id'] if isinstance(player_row, dict) else player_row[0]
        
        db_write("INSERT INTO players_by_club (club_id, player_id) VALUES (%s, %s)", (club_id, player_id))
        flash(f"Spieler {first} {last} wurde hinzugefügt.")
        return redirect(url_for('index'))
    
    clubs = db_read("SELECT id, club_name FROM clubs ORDER BY club_name ASC")
    return render_template("add_player.html", clubs=clubs)

@app.route("/add_trainer", methods=["GET", "POST"])
@login_required
def add_trainer():
    if request.method == "POST":
        first = request.form["coach_firstname"]
        last = request.form["coach_name"]
        club_id = request.form["club_id"]
        start = request.form["start_year"]
        end = request.form["end_year"]

        db_write("INSERT INTO coaches (coach_firstname, coach_name) VALUES (%s, %s)", (first, last))
        coach_row = db_read("SELECT id FROM coaches ORDER BY id DESC LIMIT 1", single=True)
        coach_id = coach_row['id'] if isinstance(coach_row, dict) else coach_row[0]

        db_write("INSERT INTO coaches_per_club (coach_id, club_id, start_year, end_year) VALUES (%s, %s, %s, %s)", (coach_id, club_id, start or None, end or None))
        flash(f"Trainer {first} {last} wurde hinzugefügt.")
        return redirect(url_for('index'))
    
    clubs = db_read("SELECT id, club_name FROM clubs ORDER BY club_name ASC")
    return render_template("add_trainer.html", clubs=clubs)

@app.route("/add_title", methods=["GET", "POST"])
@login_required
def add_title():
    if request.method == "POST":
        name = request.form["title_name"]
        year = request.form["year_"]
        club_id = request.form["club_id"]

        db_write("INSERT INTO titles (title_name) VALUES (%s)", (name,))
        title_row = db_read("SELECT id FROM titles ORDER BY id DESC LIMIT 1", single=True)
        title_id = title_row['id'] if isinstance(title_row, dict) else title_row[0]
        
        db_write("INSERT INTO titles_per_club (title_id, club_id, year_) VALUES (%s, %s, %s)", (title_id, club_id, year))
        flash(f"Titel '{name}' hinzugefügt.")
        return redirect(url_for('index'))
    
    clubs = db_read("SELECT id, club_name FROM clubs ORDER BY club_name ASC")
    return render_template("add_title.html", clubs=clubs)

if __name__ == "__main__":
    app.run()
