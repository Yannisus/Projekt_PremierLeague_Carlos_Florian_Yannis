"""Fetch Premier League data from a football API and populate DB.

This script uses FOOTBALL_API_KEY and FOOTBALL_API_BASE environment variables.
By default it targets football-data.org v2 (competition id 2021 = Premier League).

Usage:
    set env FOOTBALL_API_KEY=...
    python scripts/fetch_api.py
"""
import os
import requests
from db import db_read, db_write

API_KEY = os.getenv("FOOTBALL_API_KEY")
API_BASE = os.getenv("FOOTBALL_API_BASE", "https://api.football-data.org/v2")
HEADERS = {"X-Auth-Token": API_KEY} if API_KEY else {}

# Competition id for Premier League on football-data.org is 2021
COMPETITION_ID = 2021


def fetch_teams():
    url = f"{API_BASE}/competitions/{COMPETITION_ID}/teams"
    print("GET", url)
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    return data.get("teams", [])


def fetch_team_details(team_id):
    url = f"{API_BASE}/teams/{team_id}"
    print("GET", url)
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def upsert_club(team):
    # team: dict from API
    name = team.get("name")
    country = team.get("area", {}).get("name")
    stadium = team.get("venue") or None
    competition_id = COMPETITION_ID
    competition_name = "Premier League"
    db_write("INSERT OR IGNORE INTO clubs (name, country, stadium, competition_id, competition_name) VALUES (%s, %s, %s, %s, %s)", (name, country, stadium, competition_id, competition_name))
    # get id
    row = db_read("SELECT id FROM clubs WHERE name = %s AND competition_id = %s", (name, competition_id), single=True)
    return row and row.get("id")


def upsert_player(player, club_id=None):
    name = player.get("name")
    position = player.get("position") or player.get("role") or None
    db_write("INSERT OR IGNORE INTO players (name, club_id, position) VALUES (%s, %s, %s)", (name, club_id, position))


def upsert_trainer(coach, club_id=None):
    name = coach.get("name")
    db_write("INSERT OR IGNORE INTO trainers (name, club_id) VALUES (%s, %s)", (name, club_id))


def main():
    if not API_KEY:
        print("Warning: FOOTBALL_API_KEY not set — you can still fetch only public endpoints if available, but rate limits/missing data may occur.")

    teams = fetch_teams()
    print(f"Found {len(teams)} teams")

    for t in teams:
        club_id = upsert_club(t)
        # fetch detailed squad
        details = fetch_team_details(t.get("id"))
        squad = details.get("squad") or []
        for member in squad:
            role = member.get("role", "PLAYER")
            if role and role.upper() == "PLAYER":
                upsert_player(member, club_id)
            else:
                # treat as trainer/coach
                upsert_trainer(member, club_id)

    print("Done.")


if __name__ == "__main__":
    main()
