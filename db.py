from dotenv import load_dotenv
import os
import logging

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

        # Attempt to migrate schema (add uuid, country, stadium) for MySQL
        try:
            conn = pool.get_connection()
            cur = conn.cursor()
            
            # 1. uuid
            try:
                cur.execute("ALTER TABLE clubs ADD COLUMN uuid VARCHAR(36)")
                conn.commit()
                logging.info("Migrated MySQL: Added uuid column to clubs")
            except Exception as e:
                logging.debug("MySQL alter table (uuid) skipped: %s", e)
                
            # 2. country
            try:
                cur.execute("ALTER TABLE clubs ADD COLUMN country VARCHAR(250)")
                conn.commit()
                logging.info("Migrated MySQL: Added country column to clubs")
            except Exception as e:
                logging.debug("MySQL alter table (country) skipped: %s", e)
                
            # 3. stadium
            try:
                cur.execute("ALTER TABLE clubs ADD COLUMN stadium VARCHAR(250)")
                conn.commit()
                logging.info("Migrated MySQL: Added stadium column to clubs")
            except Exception as e:
                logging.debug("MySQL alter table (stadium) skipped: %s", e)

            cur.close()
            conn.close()
        except Exception as e:
             logging.warning("MySQL migration check failed: %s", e)

        def get_conn():
            return pool.get_connection()

        def _normalize_sql(sql: str) -> str:
            if not sql:
                return sql
            # MySQL uses `INSERT IGNORE`, SQLite uses `INSERT OR IGNORE`
            if USE_SQLITE:
                return sql.replace("INSERT IGNORE", "INSERT OR IGNORE")
            else:
                return sql.replace("INSERT OR IGNORE", "INSERT IGNORE")


        def db_read(sql, params=None, single=False):
            sql = _normalize_sql(sql)
            conn = get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(sql, params or ())

                if single:
                    row = cur.fetchone()
                    logging.debug("db_read(single=True) -> %s", row)
                    return row
                else:
                    rows = cur.fetchall()
                    logging.debug("db_read(single=False) -> %s", rows)
                    return rows

            finally:
                try:
                    cur.close()
                except:
                    pass
                conn.close()

        def db_write(sql, params=None):
            sql = _normalize_sql(sql)
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute(sql, params or ())
                conn.commit()
                logging.debug("db_write OK: %s %s", sql, params)
            finally:
                try:
                    cur.close()
                except:
                    pass
                conn.close()

        USE_SQLITE = False
    except Exception as e:
        logging.warning("MySQL setup failed, falling back to SQLite: %s", e)

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
                title TEXT,
                uuid TEXT
            )
            """
        )
        # Attempt to add uuid column if it's missing (for existing dbs)
        try:
            cur.execute("ALTER TABLE clubs ADD COLUMN uuid TEXT")
        except:
            pass
        
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
            # normalize INSERT IGNORE for sqlite
            if USE_SQLITE:
                sql = sql.replace("INSERT IGNORE", "INSERT OR IGNORE")
            cur.execute(sql, params)
        else:
            sql = sql.replace("%s", "?")
            if USE_SQLITE:
                sql = sql.replace("INSERT IGNORE", "INSERT OR IGNORE")
            cur.execute(sql)

    def db_read(sql, params=None, single=False):
        conn = get_conn()
        try:
            cur = conn.cursor()
            _exec(cur, sql, params)

            if single:
                row = cur.fetchone()
                logging.debug("db_read(single=True) -> %s", row)
                return dict(row) if row else None
            else:
                rows = cur.fetchall()
                rows = [dict(r) for r in rows]
                logging.debug("db_read(single=False) -> %s", rows)
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
            logging.debug("db_write OK: %s %s", sql, params)
        finally:
            try:
                cur.close()
            except:
                pass
            conn.close()