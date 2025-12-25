from rscanner import post_scan, pick_time, ticker_generation, sort, add_data
#from yfinance import yf

def run():
    def initial():
        print("yfinance is running")
        tickers = ticker_generation()
        time = pick_time()
        final_count, total_posts = post_scan(time, tickers)

        # Add Columns
        final_count = add_data(final_count)

        # Sort
        final_count = sort(final_count, "score")

        for ticker, stat in final_count:
            print(f"{ticker}: {stat}")

    initial()

if __name__ == "__main__":
    run()