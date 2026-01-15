from dotenv import load_dotenv
import os

# Load .env variables
load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE")
}

# Try to use MySQL if DB_HOST is set; on failure fall back to SQLite
USE_SQLITE = True
if DB_CONFIG.get("host"):
    try:
        from mysql.connector import pooling

        pool = pooling.MySQLConnectionPool(pool_name="pool", pool_size=5, **DB_CONFIG)

        def get_conn():
            return pool.get_connection()

        def db_read(sql, params=None, single=False):
            conn = get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(sql, params or ())

                if single:
                    row = cur.fetchone()
                    print("db_read(single=True) ->", row)   # DEBUG
                    return row
                else:
                    rows = cur.fetchall()
                    print("db_read(single=False) ->", rows)  # DEBUG
                    return rows

            finally:
                try:
                    cur.close()
                except:
                    pass
                conn.close()

        def db_write(sql, params=None):
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute(sql, params or ())
                conn.commit()
                print("db_write OK:", sql, params)  # DEBUG
            finally:
                try:
                    cur.close()
                except:
                    pass
                conn.close()

        USE_SQLITE = False
    except Exception as e:
        print("MySQL setup failed, falling back to SQLite:", e)

if USE_SQLITE:
    import sqlite3

    DB_FILE = os.path.join(os.path.dirname(__file__), "db.sqlite3")

    # Ensure tables exist for local development
    def _ensure_schema():
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        # Create tables aligned with MySQL schema (db/main.sql)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT,
                player_firstname TEXT,
                player_identifier TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS coaches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coach_name TEXT,
                coach_firstname TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS coaches_per_club (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coach_id INTEGER NOT NULL,
                club_id INTEGER NOT NULL,
                start_year INTEGER,
                end_year INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_name TEXT,
                name TEXT,
                country TEXT,
                stadium TEXT,
                competition_id INTEGER,
                competition_name TEXT,
                trainer TEXT,
                title TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_name TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS players_by_club (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER,
                player_id INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS titles_per_club (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year_ INTEGER,
                title_id INTEGER,
                club_id INTEGER
            )
            """
        )
        conn.commit()
        cur.close()
        conn.close()

    _ensure_schema()

    def get_conn():
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    # Allow use of %s placeholders in code; convert to ? for sqlite
    def _exec(cur, sql, params=None):
        if params:
            sql = sql.replace("%s", "?")
            cur.execute(sql, params)
        else:
            sql = sql.replace("%s", "?")
            cur.execute(sql)

    def db_read(sql, params=None, single=False):
        conn = get_conn()
        try:
            cur = conn.cursor()
            _exec(cur, sql, params)

            if single:
                row = cur.fetchone()
                print("db_read(single=True) ->", row)  # DEBUG
                return dict(row) if row else None
            else:
                rows = cur.fetchall()
                rows = [dict(r) for r in rows]
                print("db_read(single=False) ->", rows)  # DEBUG
                return rows
        finally:
            try:
                cur.close()
            except:
                pass
            conn.close()

    def db_write(sql, params=None):
        conn = get_conn()
        try:
            cur = conn.cursor()
            _exec(cur, sql, params)
            conn.commit()
            print("db_write OK:", sql, params)  # DEBUG
        finally:
            try:
                cur.close()
            except:
                pass
            conn.close()