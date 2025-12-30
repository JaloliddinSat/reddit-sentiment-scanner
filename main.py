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

def _safe_latest_price(ticker: str):
    try:
        last_price = yf.Ticker(ticker).history(period="1d", interval="1m")["Close"].iloc[-1]
        if not last_price or last_price is None:
            return None
        return float(last_price)
    except Exception:
        return None
def get_growth_table():
    select = ["stock", "price", "time_of_run"]
    db_data = print_select(select)
    final_output.clear()
    db_stock.clear()
    db_price.clear()
    db_date.clear()


    for ticker, price, date in db_data:
        db_stock.append(ticker)
        db_price.append(price)
        db_date.append(date)

    for ticker, price, date in db_data:
        price_now = float(yf.Ticker(ticker).history(period="1d", interval="1m")["Close"].iloc[-1])

        # FINAL OUTPUT
        final_output[ticker] = {
            "Price": price,
            "Original Run": date,
            "Growth %": f"{((price_now / price) - 1)}%"
        }

    final_output_list = list(final_output.items())
    df1 = pd.DataFrame(
        [
            (ticker, stats["Price"], stats["Original Run"], stats["Growth %"])
            for ticker, stats in final_output_list
        ],
        columns=["Ticker", "Price", "Original Run", "Growth%"]
    )

    return final_output_list, df1
def run_full_pipeline():
    # Process
    top_3 = main_rscanner()[:3]
    top_3 = add_financials(top_3)

    # import to SQL database
    main_database(top_3)

    return get_growth_table()

def main():
    _, df = run_full_pipeline()
    print(f"Sorted by Score: \n {df} \n")






if __name__ == "__main__":
    main()