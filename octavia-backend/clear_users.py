import sqlite3
conn = sqlite3.connect('dev.db')
c = conn.cursor()
c.execute("DELETE FROM users")
conn.commit()
print('users table cleared')
conn.close()
