import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

print("=== All clubs ===")
cur.execute("SELECT id, name, competition_id FROM clubs LIMIT 10")
print(cur.fetchall())

print("\n=== Manchester clubs (case insensitive) ===")
cur.execute("SELECT id, name, competition_id FROM clubs WHERE name LIKE ?", ('%manchester%',))
print(cur.fetchall())

print("\n=== Manchester City search ===")
cur.execute("SELECT id, name, competition_id FROM clubs WHERE name LIKE ?", ('%Manchester City%',))
print(cur.fetchall())

print("\n=== Testing the actual search query ===")
cur.execute("SELECT id, name, country, stadium, competition_name FROM clubs WHERE name LIKE ? AND competition_id = ?", ('%manchester city%', 2021))
print(cur.fetchall())

conn.close()
