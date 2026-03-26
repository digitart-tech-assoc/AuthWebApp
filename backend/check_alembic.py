#!/usr/bin/env python
"""Check alembic_version table and update migration history."""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load env vars
project_root = Path(__file__).resolve().parent.parent
env_file = project_root / '.env'
if env_file.exists():
    load_dotenv(env_file)

import psycopg2

db_url = os.getenv('DATABASE_URL')
print(f"Database URL: {db_url[:50]}...")

# Connect to database
conn = psycopg2.connect(db_url)
cur = conn.cursor()

try:
    # Check if alembic_version table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'alembic_version'
        )
    """)
    table_exists = cur.fetchone()[0]
    print(f"alembic_version table exists: {table_exists}")

    if not table_exists:
        # Create alembic_version table
        print("Creating alembic_version table...")
        cur.execute("""
            CREATE TABLE alembic_version (
                version_num VARCHAR(32) NOT NULL, 
                PRIMARY KEY (version_num)
            )
        """)
        conn.commit()
        print("alembic_version table created")

    # Check current migration versions
    cur.execute("SELECT version_num FROM alembic_version")
    versions = cur.fetchall()
    print(f"Applied migrations: {versions}")

    # If 0001_initial migration is not in the table, add it
    if versions and ('0001_initial',) not in versions:
        print("Adding 0001_initial to alembic_version...")
        cur.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", ('0001_initial',))
        conn.commit()
        print("0001_initial migration marked as applied")
    elif not versions:
        print("No migrations applied yet. Adding 0001_initial...")
        cur.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", ('0001_initial',))
        conn.commit()
        print("0001_initial migration marked as applied")

finally:
    cur.close()
    conn.close()

print("Done!")
