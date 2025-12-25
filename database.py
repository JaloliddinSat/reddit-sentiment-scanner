import sqlite3
from sqlite3 import connect

from setuptools.installer import fetch_build_egg

conn = sqlite3.connect("database.db")
curr = conn.cursor()

#creation of the data table
command1 = "CREATE TABLE IF NOT EXISTS database (stock TEXT, mentions INTEGER, time_of_run TEXT)"
curr.execute(command1)

def insert_db(par1, par2, par3):
    sql_insert = "INSERT INTO database (stock, mentions, time_of_run) VALUES (?, ?, ?)"
    curr.execute(sql_insert, (par1, par2, par3))

def print_select(col):
    allowed = ["stock", "mentions", "time_of_run"]

    if isinstance(col, str):
        curr.execute(f"SELECT {col} FROM database")
    else:
        for c in col:
            if c not in allowed:
                raise ValueError("Wrong value:" + c)
        cols_sql = ", ".join(col)
        curr.execute(f"SELECT {cols_sql} FROM database")

    results = curr.fetchall()
    return results

fetch_input = ["stock", "mentions", "time_of_run"]

print(print_select(fetch_input))

conn.commit()
conn.close()