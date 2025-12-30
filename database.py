from rscanner import ticker_generation, pick_time, post_scan, add_data, sort
import sqlite3
from sqlite3 import connect
from setuptools.installer import fetch_build_egg

DB_PATH = "user_database.db"
CREATE_SQL = "CREATE TABLE IF NOT EXISTS scan_input (stock TEXT, score INTEGER, time_of_run TEXT, price FLOAT)"

# function
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_SQL)
    return conn
def insert_db(par1, par2, par3, par4):
    conn = _connect()
    curr = conn.cursor()

    sql_insert = "INSERT INTO scan_input (stock, score, time_of_run, price) VALUES (?, ?, ?, ?)"
    curr.execute(sql_insert, (par1, par2, par3, par4))

    conn.commit()
    conn.close()
def print_select(arg):
    allowed = ["stock", "score", "time_of_run", "price"]

    conn = _connect()
    curr = conn.cursor()

    if isinstance(arg, str):
        if arg not in allowed:
            conn.close()
            raise ValueError("Wrong value:" + arg)
        curr.execute(f"SELECT {arg} FROM scan_input")
    else:
        for a in arg:
            if a not in allowed:
                conn.close()
                raise ValueError("Wrong value:" + a)
        args_sql = ", ".join(arg)
        curr.execute(f"SELECT {args_sql} FROM scan_input")

    results = curr.fetchall()
    conn.close()
    return results
def gather_values(rscanner_data):
    ticker = rscanner_data[0]
    score = rscanner_data[1]["score"]
    date = rscanner_data[1]["date"]
    price = rscanner_data[1]["price"]
    return ticker, score, date, price
def main_database(top_3):
    if not top_3:
        print("No tickers are inserted to database.")

    db_ticker_list = print_select("stock")

    for idx, item in enumerate(top_3[:3], start=1):
        ticker, score, date, price = gather_values(item)

        if (ticker,) not in db_ticker_list:
            insert_db(ticker, score, date, price)
            print(f"{ticker} was added from ticker{idx}!")