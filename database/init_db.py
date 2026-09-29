"""Create and seed the SPARC Textbook Studio database.

Usage (from the project root, with .venv active):
    python database/init_db.py                 # schema + seed data
    python database/init_db.py --schema-only   # empty tables

The engine comes from the DATABASE_ENGINE environment variable:
    sqlite (default)  -> database/sparc.db
    mysql             -> the database named in JAWSDB_URL

This script never drops, deletes, or overwrites anything. If the target
database already has SPARC tables (or sparc.db already exists), it stops
with an error; removing the old database is a deliberate, manual step.
"""

import argparse
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

DATABASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
SEED_PATH = DATABASE_DIR / "seed_data.sql"
DEFAULT_SQLITE_PATH = DATABASE_DIR / "sparc.db"


def read_scripts(include_seed: bool) -> list[str]:
    """Return the SQL file contents to run, in order (schema, then seed)."""
    paths = [SCHEMA_PATH, SEED_PATH] if include_seed else [SCHEMA_PATH]
    return [path.read_text(encoding="utf-8") for path in paths]


def table_names(schema_sql: str) -> list[str]:
    """Return the table names created by schema.sql, in creation order."""
    return re.findall(r"CREATE TABLE (\w+)", schema_sql)


def split_statements(sql_text: str) -> list[str]:
    """Split a SQL script into single statements for drivers that need that.

    Whole-line "--" comments are dropped first. A statement ends at a ";"
    that closes its line, so semicolons inside text values ("coast; Macon")
    are left alone.
    """
    code_lines = [line for line in sql_text.splitlines() if not line.lstrip().startswith("--")]
    chunks = re.split(r";[ \t]*$", "\n".join(code_lines), flags=re.MULTILINE)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def to_mysql(statement: str) -> str:
    """Translate the one SQLite-only keyword in schema.sql to MySQL."""
    return re.sub(r"\bAUTOINCREMENT\b", "AUTO_INCREMENT", statement)


def count_rows(conn, tables: list[str]) -> dict[str, int]:
    """Return {table: row count}. Works with sqlite3 and PyMySQL connections."""
    cursor = conn.cursor()
    counts = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    return counts


def init_sqlite(db_path: Path, scripts: list[str], tables: list[str]) -> dict[str, int]:
    """Build a new SQLite database at db_path and return row counts.

    Builds into a temp file in the same folder and renames it into place only
    after every statement succeeds, so a failed run never leaves a
    half-built sparc.db behind.

    Raises FileExistsError if db_path already exists.
    Raises sqlite3.IntegrityError if the seed data breaks a foreign key.
    """
    if db_path.exists():
        raise FileExistsError(
            f"{db_path} already exists. Delete it yourself first if you want a fresh database."
        )

    fd, tmp_name = tempfile.mkstemp(dir=db_path.parent, suffix=".db.tmp")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        conn = sqlite3.connect(tmp_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            for script in scripts:
                conn.executescript(script)
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise sqlite3.IntegrityError(f"Foreign key violations: {violations}")
            counts = count_rows(conn, tables)
        finally:
            conn.close()
        os.replace(tmp_path, db_path)
        return counts
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def mysql_connect(db_url: str):
    """Open a PyMySQL connection from a mysql://user:pass@host:port/db URL."""
    import pymysql

    parsed = urlparse(db_url)
    return pymysql.connect(
        host=parsed.hostname,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/"),
        port=parsed.port or 3306,
        charset="utf8mb4",
    )


def existing_mysql_tables(conn, tables: list[str]) -> list[str]:
    """Return which of the given tables already exist in the current MySQL database."""
    placeholders = ", ".join(["%s"] * len(tables))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        f"WHERE table_schema = DATABASE() AND table_name IN ({placeholders})",
        tables,
    )
    return [row[0] for row in cursor.fetchall()]


def init_mysql(db_url: str, scripts: list[str], tables: list[str]) -> dict[str, int]:
    """Create and seed the SPARC tables in MySQL and return row counts.

    MySQL commits each CREATE TABLE immediately, so a failure partway through
    can leave some tables behind; the error says which statement failed.

    Raises FileExistsError if any SPARC table already exists.
    """
    conn = mysql_connect(db_url)
    try:
        found = existing_mysql_tables(conn, tables)
        if found:
            raise FileExistsError(
                f"These tables already exist in the MySQL database: {', '.join(found)}. "
                "Drop them yourself first if you want a fresh database."
            )
        cursor = conn.cursor()
        for script in scripts:
            for statement in split_statements(script):
                try:
                    cursor.execute(to_mysql(statement))
                except Exception as exc:
                    first_line = statement.splitlines()[0]
                    raise RuntimeError(f"MySQL failed on: {first_line} ... ({exc})") from exc
        conn.commit()
        return count_rows(conn, tables)
    finally:
        conn.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line flags."""
    parser = argparse.ArgumentParser(description="Create and seed the SPARC database.")
    parser.add_argument("--schema-only", action="store_true", help="create tables without seed data")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=DEFAULT_SQLITE_PATH,
        help="SQLite file to create (default: database/sparc.db)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Run the init for the configured engine. Returns a process exit code."""
    args = parse_args(argv)
    load_dotenv(DATABASE_DIR.parent / ".env")
    engine = os.getenv("DATABASE_ENGINE", "sqlite").strip().lower()

    scripts = read_scripts(include_seed=not args.schema_only)
    tables = table_names(scripts[0])

    try:
        if engine == "sqlite":
            print(f"Creating SQLite database at {args.sqlite_path}")
            counts = init_sqlite(args.sqlite_path, scripts, tables)
        elif engine == "mysql":
            db_url = os.getenv("JAWSDB_URL")
            if not db_url:
                print("DATABASE_ENGINE=mysql but JAWSDB_URL is not set. See .env.example.")
                return 1
            print("Creating tables in MySQL (JAWSDB_URL)")
            counts = init_mysql(db_url, scripts, tables)
        else:
            print(f"Unknown DATABASE_ENGINE '{engine}'. Use 'sqlite' or 'mysql'.")
            return 1
    except (FileExistsError, RuntimeError, sqlite3.Error) as exc:
        print(f"Stopped: {exc}")
        return 1

    for table, count in counts.items():
        print(f"  {table:<20} {count} rows")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
