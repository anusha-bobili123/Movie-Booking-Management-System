"""
Run this script ONCE to add the new cancellation/reply/refund columns
to your existing PostgreSQL contact_messages table.

Usage:
    python migrate_add_cancellation_columns.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from database.db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        cols = [
            ("contact_messages", "is_cancellation", "BOOLEAN DEFAULT FALSE"),
            ("contact_messages", "booking_id",       "INTEGER"),
            ("contact_messages", "refund_status",    "VARCHAR(30)"),
            ("contact_messages", "admin_reply",      "TEXT"),
            ("contact_messages", "replied_at",       "TIMESTAMP"),
            ("user_bookings",    "cancel_reason",    "VARCHAR(500)"),
        ]
        for table, col, col_type in cols:
            try:
                with conn.begin_nested():
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
                print(f"  ✅  {table}.{col}  added")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"  ⏭   {table}.{col}  already exists — skipped")
                else:
                    print(f"  ❌  {table}.{col}  failed: {e}")

    print("\nDone. You can now restart your Flask app.")
