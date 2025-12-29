import yfinance as yf
from pycparser.ply.ctokens import t_PLUS
from rscanner import main_rscanner
import pandas as pd
from database import main_database

# Functions
def add_financials(top_3):
    for ticker, stats in top_3:
        last_price = yf.Ticker(ticker).history(period="1d", interval="1m")["Close"].iloc[-1]
        stats["price"] = float(last_price)
        print(float(last_price))

    return top_3

def main_main():
    print("Main is runnning.")

    # Process
    top_3 = main_rscanner()[:3]
    top_3 = add_financials(top_3)

    # import to SQL database
    main_database(top_3)

    df1 = pd.DataFrame(
        [
            (ticker, stats["mentions"], stats["bull"], stats["bear"], stats["signal"], stats["interpret"], stats["score"], stats["date"], stats["price"])
            for ticker, stats in top_3
        ],
        columns=["Ticker", "Mentions", "Bull", "Bear", "Signal", "Conclusion", "Score", "Date", "Price"]
    )

    print(f"Sorted by Score: \n {df1[:10]} \n")

    print(top_3)


if __name__ == "__main__":
    main_main()