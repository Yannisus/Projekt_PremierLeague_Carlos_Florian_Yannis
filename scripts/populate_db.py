import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db import db_write

# Sample clubs with competition_id set to Premier League (2021)
clubs = [
    ("Arsenal", "England", "Emirates Stadium"),
    ("Manchester United", "England", "Old Trafford"),
    ("Liverpool", "England", "Anfield"),
]

for c in clubs:
    db_write("INSERT OR IGNORE INTO clubs (name, country, stadium, competition_id, competition_name) VALUES (%s, %s, %s, %s, %s)", (c[0], c[1], c[2], 2021, 'Premier League'))

# Sample players
players = [
    ("Bukayo Saka", 1, "Winger"),
    ("Marcus Rashford", 2, "Forward"),
    ("Mohamed Salah", 3, "Forward"),
]
for p in players:
    db_write("INSERT INTO players (name, club_id, position) VALUES (%s, %s, %s)", p)

print('Sample data inserted')