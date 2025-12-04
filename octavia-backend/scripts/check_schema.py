"""Check database schema for jobs table."""
from app import db
import sqlite3

conn = sqlite3.connect('dev.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(jobs)")
columns = cursor.fetchall()
print("Columns in jobs table:")
for col in columns:
    print(f"  {col}")
conn.close()
