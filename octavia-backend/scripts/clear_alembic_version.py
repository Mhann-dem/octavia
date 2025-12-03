import sqlite3
conn = sqlite3.connect('dev.db')
c = conn.cursor()
c.execute("DELETE FROM alembic_version")
conn.commit()
print('alembic_version cleared')
conn.close()
