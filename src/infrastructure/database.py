import os
from peewee import SqliteDatabase
from pathlib import Path

# Ensure db directory exists
DB_DIR = Path("db")
DB_DIR.mkdir(exist_ok=True)

DATABASE_FILE = DB_DIR / "schulware.db"
database = SqliteDatabase(DATABASE_FILE)
