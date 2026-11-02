"""Database connection, setup and seeding."""
import json
import os
import sqlite3

from models import SCHEMA

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)


def load_env():
    """Tiny .env loader (no extra dependency)."""
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


load_env()


def db_path():
    return os.environ.get("PORTAL_DB", os.path.join(ROOT, "database", "portal.db"))


def upload_dir():
    return os.environ.get("UPLOAD_DIR", os.path.join(ROOT, "uploads"))


def get_db():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(db_path()), exist_ok=True)
    os.makedirs(upload_dir(), exist_ok=True)
    with get_db() as db:
        db.executescript(SCHEMA)
        if db.execute("SELECT COUNT(*) FROM internships").fetchone()[0] == 0:
            seed(db)


def seed(db):
    path = os.path.join(ROOT, "data", "sample_internships.json")
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    for i in items:
        db.execute(
            """INSERT INTO internships (title, company, location, domain, duration_months,
               stipend, work_mode, description, requirements, benefits, deadline)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (i["title"], i["company"], i["location"], i["domain"], i["duration_months"],
             i["stipend"], i["work_mode"], i["description"],
             "\n".join(i["requirements"]), "\n".join(i["benefits"]), i["deadline"]),
        )
