import sqlite3

conn = sqlite3.connect("gwp_data.db")
c = conn.cursor()
for row in c.execute("SELECT * FROM gwp_values"):
    print(row)
conn.close()
