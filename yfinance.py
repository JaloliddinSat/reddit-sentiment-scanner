from rscanner import post_scan, pick_time, ticker_generation

def run():
    def main_run():
        print("yfinance is running")
        tickers = ticker_generation()
        time = pick_time()
        final_count, total_posts = post_scan(time, tickers)

        return final_count, total_posts

    main_run()

if __name__ == "__main__":
    run()