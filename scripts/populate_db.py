import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db import db_write

# Sample clubs
clubs = [
    ("Arsenal", "England", "Emirates Stadium"),
    ("Manchester United", "England", "Old Trafford"),
    ("Liverpool", "England", "Anfield"),
]

for c in clubs:
    db_write("INSERT OR IGNORE INTO clubs (name, country, stadium) VALUES (%s, %s, %s)", c)

# Sample players
players = [
    ("Bukayo Saka", 1, "Winger"),
    ("Marcus Rashford", 2, "Forward"),
    ("Mohamed Salah", 3, "Forward"),
]
for p in players:
    db_write("INSERT INTO players (name, club_id, position) VALUES (%s, %s, %s)", p)

print('Sample data inserted')