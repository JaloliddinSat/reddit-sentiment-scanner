import yfinance as yf
import pandas as pd
from pycparser.ply.ctokens import t_PLUS
from rscanner import main_rscanner
from database import main_database, print_select

final_output = {}
db_stock = []
db_price = []
db_date = []

# Functions
def add_financials(input_list):
    for ticker, stats in input_list:
        last_price = yf.Ticker(ticker).history(period="1d", interval="1m")["Close"].iloc[-1]
        stats["price"] = float(last_price)

    return input_list

def main_main():
    print("Main is runnning.")

    # Process
    top_3 = main_rscanner()[:3]
    top_3 = add_financials(top_3)

    # import to SQL database
    main_database(top_3)
    select = ["stock", "price", "time_of_run"]
    db_data = print_select(select)

    for ticker, price, date in db_data:
        db_stock.append(ticker)
        db_price.append(price)
        db_date.append(date)

    # print(db_data)
    # print(f"\n{db_stock}")
    # print(f"{db_price}\n")

    # FINAL OUTPUT
    for ticker, price, date in db_data:
        price_now = float(yf.Ticker(ticker).history(period="1d", interval="1m")["Close"].iloc[-1])
        final_output[ticker] = {
            "Price": price,
            "Original Run": date,
            "Growth %": f"{((price / price_now) - 1)}%"
        }

    final_output_list = list(final_output.items())

    df1 = pd.DataFrame(
        [
            (ticker, stats["Price"], stats["Original Run"], stats["Growth %"])
            for ticker, stats in final_output_list
        ],
        columns=["Ticker", "Price", "Original Run", "Growth%"]
    )

    print(f"Sorted by Score: \n {df1} \n")

if __name__ == "__main__":
    main_main()