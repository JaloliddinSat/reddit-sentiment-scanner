import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "user_database.db"))
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS scan_input (
    stock TEXT,
    mentions INTEGER,
    bull INTEGER,
    bear INTEGER,
    score INTEGER,
    time_of_run TEXT,
    price FLOAT
)
"""
# function
def _connect():

    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_SQL)
    return conn
def insert_db(par1, par2, par3, par4, par5, par6, par7):
    conn = _connect()
    curr = conn.cursor()

    sql_insert = """
    INSERT INTO scan_input (stock, mentions, bull, bear, score, time_of_run, price)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    curr.execute(sql_insert, (par1, par2, par3, par4, par5, par6, par7))

    conn.commit()
    conn.close()

def print_select(arg):
    allowed = ["stock", "mentions", "bull", "bear", "score", "time_of_run", "price"]

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
    stats = rscanner_data[1]

    mentions = stats["mentions"]
    bull = stats["bull"]
    bear = stats["bear"]
    score = stats["score"]
    date = stats["date"]
    price = stats["price"]

    # matches INSERT column order
    return ticker, mentions, bull, bear, score, date, price

def main_database(top_3):
    if not top_3:
        print("No tickers are inserted to database.")

    db_ticker_list = print_select("stock")

    for idx, item in enumerate(top_3[:3], start=1):
        ticker, mentions, bull, bear, score, date, price = gather_values(item)

        if (ticker,) not in db_ticker_list:
            insert_db(ticker, mentions, bull, bear, score, date, price)
            print(f"{ticker} was added from ticker{idx}!")