import sys
import os
import uuid

# Fix imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_app import app
from db import db_write, db_read, _ensure_schema

print("Seeding database...")

# Ensure tables exist (in case of fresh sqlite)
_ensure_schema()

# Sample Data
clubs_data = [
    {"name": "Manchester City", "country": "England", "stadium": "Etihad Stadium"},
    {"name": "Arsenal FC", "country": "England", "stadium": "Emirates Stadium"},
    {"name": "Liverpool FC", "country": "England", "stadium": "Anfield"},
    {"name": "Aston Villa", "country": "England", "stadium": "Villa Park"},
    {"name": "Tottenham Hotspur", "country": "England", "stadium": "Tottenham Hotspur Stadium"}
]

players_data = [
    {"name": "Haaland", "firstname": "Erling", "club": "Manchester City"},
    {"name": "De Bruyne", "firstname": "Kevin", "club": "Manchester City"},
    {"name": "Saka", "firstname": "Bukayo", "club": "Arsenal FC"},
    {"name": "Odegaard", "firstname": "Martin", "club": "Arsenal FC"},
    {"name": "Salah", "firstname": "Mohamed", "club": "Liverpool FC"},
    {"name": "Watkins", "firstname": "Ollie", "club": "Aston Villa"},
    {"name": "Son", "firstname": "Heung-min", "club": "Tottenham Hotspur"}
]

trainers_data = [
    {"name": "Guardiola", "firstname": "Pep", "club": "Manchester City", "start": 2016},
    {"name": "Arteta", "firstname": "Mikel", "club": "Arsenal FC", "start": 2019},
    {"name": "Klopp", "firstname": "Jurgen", "club": "Liverpool FC", "start": 2015},
    {"name": "Emery", "firstname": "Unai", "club": "Aston Villa", "start": 2022},
    {"name": "Postecoglou", "firstname": "Ange", "club": "Tottenham Hotspur", "start": 2023}
]

titles_data = [
    {"title": "Premier League", "year": 2023, "club": "Manchester City"},
    {"title": "Champions League", "year": 2023, "club": "Manchester City"},
    {"title": "FA Cup", "year": 2020, "club": "Arsenal FC"},
    {"title": "Premier League", "year": 2020, "club": "Liverpool FC"}
]

with app.app_context():
    # Insert Clubs
    for c in clubs_data:
        # Check if exists
        check = db_read("SELECT id FROM clubs WHERE club_name=%s", (c['name'],), single=True)
        if not check:
            u_id = str(uuid.uuid4())
            db_write("INSERT INTO clubs (club_name, country, stadium, uuid) VALUES (%s, %s, %s, %s)", 
                     (c['name'], c['country'], c['stadium'], u_id))
            print(f"Added Club: {c['name']}")

    # Helper to get club id
    def get_club_id(name):
        row = db_read("SELECT id FROM clubs WHERE club_name=%s", (name,), single=True)
        return row['id'] if isinstance(row, dict) else row[0]

    # Insert Players
    for p in players_data:
        c_id = get_club_id(p['club'])
        # check if player exists (simple check)
        check = db_read("SELECT id FROM players WHERE player_name=%s AND player_firstname=%s", (p['name'], p['firstname']), single=True)
        if not check:
            db_write("INSERT INTO players (player_name, player_firstname, player_identifier) VALUES (%s, %s, %s)", 
                     (p['name'], p['firstname'], f"{p['firstname']}{p['name']}".lower()))
            # get new id
            new_p = db_read("SELECT id FROM players WHERE player_name=%s ORDER BY id DESC LIMIT 1", (p['name'],), single=True)
            p_id = new_p['id'] if isinstance(new_p, dict) else new_p[0]
            db_write("INSERT INTO players_by_club (club_id, player_id) VALUES (%s, %s)", (c_id, p_id))
            print(f"Added Player: {p['firstname']} {p['name']}")

    # Insert Trainers
    for t in trainers_data:
        c_id = get_club_id(t['club'])
        check = db_read("SELECT id FROM coaches WHERE coach_name=%s", (t['name'],), single=True)
        if not check:
            db_write("INSERT INTO coaches (coach_name, coach_firstname) VALUES (%s, %s)", (t['name'], t['firstname']))
            new_t = db_read("SELECT id FROM coaches ORDER BY id DESC LIMIT 1", single=True)
            t_id = new_t['id'] if isinstance(new_t, dict) else new_t[0]
            db_write("INSERT INTO coaches_per_club (coach_id, club_id, start_year) VALUES (%s, %s, %s)", (t_id, c_id, t['start']))
            print(f"Added Trainer: {t['firstname']} {t['name']}")

    # Insert Titles
    for ti in titles_data:
        c_id = get_club_id(ti['club'])
        # Simplified check: assumes we can duplicate title names in titles table, just linking specific instances
        db_write("INSERT INTO titles (title_name) VALUES (%s)", (ti['title'],))
        new_ti = db_read("SELECT id FROM titles ORDER BY id DESC LIMIT 1", single=True)
        ti_id = new_ti['id'] if isinstance(new_ti, dict) else new_ti[0]
        db_write("INSERT INTO titles_per_club (title_id, club_id, year_) VALUES (%s, %s, %s)", (ti_id, c_id, ti['year']))
        print(f"Added Title: {ti['title']} for {ti['club']}")

print("Seeding complete.")
