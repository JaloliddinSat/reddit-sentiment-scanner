from rscanner import ticker_generation, pick_time, post_scan, add_data, sort
import sqlite3
from sqlite3 import connect
from setuptools.installer import fetch_build_egg

conn = sqlite3.connect("user_database.db")
curr = conn.cursor()

#creation of the data table
command1 = "CREATE TABLE IF NOT EXISTS scan_input (stock TEXT, score INTEGER, time_of_run TEXT, price FLOAT)"
curr.execute(command1)

# functions
def database_process(top_3):

    conn = sqlite3.connect("user_database.db")
    curr = conn.cursor()

    # creation of the data table
    command1 = "CREATE TABLE IF NOT EXISTS scan_input (stock TEXT, score INTEGER, time_of_run TEXT)"
    curr.execute(command1)




def initial():
    print("yfinance is running")
    tickers = ticker_generation()
    time = pick_time()
    final_count, total_posts = post_scan(time, tickers)

    # Add Columns
    final_count = add_data(final_count)

    # Sort
    if final_count:
        final_count = sort(final_count, "score")
        return final_count
    else:
        return []
def insert_db(par1, par2, par3, par4):
    sql_insert = "INSERT INTO scan_input (stock, score, time_of_run, price) VALUES (?, ?, ?, ?)"
    curr.execute(sql_insert, (par1, par2, par3, par4))
def print_select(col):
    allowed = ["stock", "score", "time_of_run"]

    if isinstance(col, str):
        curr.execute(f"SELECT {col} FROM scan_input")
    else:
        for c in col:
            if c not in allowed:
                raise ValueError("Wrong value:" + c)
        cols_sql = ", ".join(col)
        curr.execute(f"SELECT {cols_sql} FROM scan_input")

    results = curr.fetchall()
    return results
def gather_values(rscanner_data):
    ticker = rscanner_data[0]
    score = rscanner_data[1]["score"]
    date = rscanner_data[1]["date"]
    price = rscanner_data[1]["price"]

    return ticker, score, date, price

def main_database(top_3):




    db_ticker_list = print_select("stock")

    ticker1, ticker1_score, ticker1_date, ticker1_price = gather_values(top_3[0])
    if (ticker1,) not in db_ticker_list:
        insert_db(ticker1, ticker1_score, ticker1_date, ticker1_price)
        print(f"{ticker1} was added from ticker1!")

    ticker2, ticker2_score, ticker2_date, ticker2_price = gather_values(top_3[1])
    if (ticker2,) not in db_ticker_list:
        insert_db(ticker2, ticker2_score, ticker2_date, ticker2_price)
        print(f"{ticker2} was added from ticker2!")

    ticker3, ticker3_score, ticker3_date, ticker3_price = gather_values(top_3[2])
    if (ticker3,) not in db_ticker_list:
        insert_db(ticker3, ticker3_score, ticker3_date, ticker3_price)
        print(f"{ticker3} was added from ticker3!")

    # print(ticker1, ticker1_score, ticker1_date)
    # print(ticker2, ticker2_score, ticker2_date)
    # print(ticker3, ticker3_score, ticker3_date)

    conn.commit()
    conn.close()

