"""Initialize the MySQL database using `db/main.sql`.

Requires environment variables: DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE

Usage:
  python scripts/init_mysql_db.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_DATABASE")
SQL_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "main.sql")

if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE]):
    print("Missing one or more DB_* environment variables. Please set DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE.")
    raise SystemExit(1)

try:
    import mysql.connector
except Exception as e:
    print("Please install mysql-connector-python (pip install mysql-connector-python)")
    raise

print(f"Connecting to MySQL host {DB_HOST} as {DB_USER}...")
cnx = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
cur = cnx.cursor()
# ensure database exists
cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_DATABASE}`")
cnx.database = DB_DATABASE

# Read SQL file and execute statements
with open(SQL_FILE, "r", encoding="utf-8") as fh:
    sql = fh.read()

print(f"Executing SQL from {SQL_FILE}...")
for result in cur.execute(sql, multi=True):
    # iterate results to ensure execution
    pass
cnx.commit()
cur.close()
cnx.close()
print("Database initialized successfully.")
