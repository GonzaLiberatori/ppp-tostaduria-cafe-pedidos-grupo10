import sqlite3

conn = sqlite3.connect('db.sqlite')
c = conn.cursor()
c.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = c.fetchall()
for t in tables:
    print(t[0])
conn.close()