import sqlite3
import pandas as pd

conn = sqlite3.connect("data/quintas.db")

df = pd.read_sql_query("SELECT * FROM quintas LIMIT 10;", conn)
print(df)

conn.close()