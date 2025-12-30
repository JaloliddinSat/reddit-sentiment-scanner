from dotenv import load_dotenv
load_dotenv()
from datetime import date
from pathlib import Path
import praw
import time
import sqlite3
import os

#HardLock
HARDLOCK_MINUTES_BACK = 10000

#Date
now_date = date.today().isoformat()

# Data Base
conn = sqlite3.connect("user_database.db")
cursor = conn.cursor()

# Reddit API
reddit = praw.Reddit(
    client_id = os.getenv("REDDIT_CLIENT_ID"),
    client_secret = os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent = "reddit_scraper"
)
if not os.getenv("REDDIT_CLIENT_ID") or  not os.getenv("REDDIT_CLIENT_SECRET"):
    raise ValueError("Missing Reddit API keys. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET.")

# Banks
sub = reddit.subreddit("valueinvesting+stocks+investing+"
                       "securityanalysis+stockanalysis+finance+"
                       "financialindependence+dividends+"
                       "personalfinancecanada+canadianinvestor+"
                       "thetagang+robinhood")
Bull = [
    "buy", "buying", "bought", "load up", "loading up", "add", "adding", "added",
    "accumulate", "accumulating", "scale in", "long", "going long", "call", "calls",
    "leap", "leaps", "bullish", "undervalued", "oversold", "breakout", "break out",
    "support bounce", "reversal", "rally", "pump", "rip", "moon", "mooning", "rocket",
    "rocketing", "skyrocket", "sending", "send it", "all in", "double down",
    "bag secured", "re-enter", "strong buy", "accumulation", "bull market",
    "trend up", "bull flag", "bull run", "to the moon", "stonks", "yolo", "tendies",
    "diamond hands", "hodl", "hypergrowth", "running", "launch", "launching",
    "multibagger", "10x", "🚀", "📈", "⬆️", "green"
]
Bear = [
    "sell", "selling", "sold", "exit", "cut", "cutting", "take profit", "reduce",
    "reducing", "trim", "trimming", "scale out", "close", "closing", "stop loss",
    "dump", "dumping", "bearish", "overvalued", "overbought", "breakdown",
    "break down", "reject", "rejection", "collapse", "crash", "crashing",
    "tank", "tanked", "tanking", "plummet", "falling", "sell-off", "downtrend",
    "lower lows", "bear market", "bear flag", "support broken", "paper hands",
    "rug pull", "rugged", "doom", "doomed", "rekt", "death candle", "liquidation",
    "panic sell", "panic selling", "fear", "fud", "bagholder", "bag holding",
    "puts", "short", "shorting", "bear raid", "sell signal", "dead cat bounce",
    "📉", "⬇️", "red"
]
ignore_words = ["CUZ", "ALOT", "TFSA"]

# English Words + Tickers
def english_words(file="words.txt"):
    base = Path(__file__).resolve().parent.parent
    path = base / "data" / file

    english_words = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.upper().strip()
            if line:
                english_words.append(line)
    return english_words
def ticker_generation(path="ticker.csv"):
    path = Path(__file__).resolve().parent.parent / "data" / "ticker.csv"
    tickers = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line:
                ticker = line.split(",", 1)[0].strip().upper()
                tickers.append(ticker)
            else:
                continue
    return tickers

tickers = ticker_generation()
english_words = english_words()

# Functions
def check_for_bull(post_text, bull_words):
    if not post_text:
        return 0
    text = post_text.lower()
    count = 0
    for w in bull_words:
        if w in text:
            count += 1
    return count
def check_for_bear(post_text, bear_words):
    count = 0
    if not post_text:
        return 0
    text = post_text.lower()
    for w in bear_words:
        if w in text:
            count += 1
    return count
def pick_time():
    return time.time() - (HARDLOCK_MINUTES_BACK * 60)

    # if minutes_back is None:
    #     usertime = input("How many minutes in the past do you want to go back?: ")
    #     while (not (usertime.isdigit()) or (not 0 < (int(usertime)) < 1000000)):
    #         usertime = input("How many minutes in the past do you want to go back?: ")
    #
    # time_rollback = int(usertime) * 60
    # current_date = time.time()
    # end_date = current_date - time_rollback
    # return end_date


def sort(list1, method):
    allowed_methods = ["mentions", "bull", "bear", "score"]
    if method not in allowed_methods:
        raise ValueError("Please pick a proper method of sort.")
    sorted_final = sorted(
        list1.items(),
        key=lambda x: x[1][method],
        reverse=True)
    return sorted_final
def add_data(final_count_list):
    for ticker, stats in final_count_list.items():
        signal = (stats["bull"] - stats["bear"]) / (stats["mentions"] + 1)

        stats["signal"] = signal
        stats["score"] = stats["signal"] * stats["mentions"]
        stats["date"] = now_date

        if stats["mentions"] < 3:
            stats["interpret"] = "Low Data"
        elif stats["score"] >= 3:
            stats["interpret"] = "Strong Bullish"
        elif stats["score"] <= -3:
            stats["interpret"] = "Strong Bearish"
        else:
            stats["interpret"] = "Weak"

    if not final_count_list:
        print("No results.")
        return

    return final_count_list
def post_scan(end_date, ticker_list):
    error_message = ("No data was collected.")
    print("_________________________________________________________________")
    print("Running Scan...")
    total_posts = 0

    ticker_count = {}
    for t in tickers:
        ticker_count[t] = {
            "mentions": 0,
            "bull": 0,
            "bear": 0
        }

    non_zero = {}
    final_count = {}

    for i in sub.new(limit=10000):
        print("Looking for any matches...")
        if i.created_utc < end_date:
            break
        else:
            text_u = (i.selftext or "").upper()
            title_u = (i.title or "").upper()
            matched = []

            for t in ticker_list:
                t1 = f" {t} "
                t2 = f"${t} "
                first_wave = (t1 in text_u) or (t1 in title_u)
                second_wave = (t2 in text_u) or (t2 in title_u)
                if first_wave or second_wave:
                    print(f"{t} detected.")
                    matched.append(t)
                    ticker_count[t]["mentions"] += 1

            if matched:
                bull_hits = check_for_bull(i.selftext, Bull)
                bear_hits = check_for_bear(i.selftext, Bear)
                for t in matched:
                    ticker_count[t]["bull"] += bull_hits
                    ticker_count[t]["bear"] += bear_hits

            total_posts += 1

    # Remove zero-mentioned tickers
    for ticker, stats in ticker_count.items():
        if stats["mentions"] != 0:
            non_zero[ticker] = stats

    # Filter english/ignore_words list
    for ticker, stats in non_zero.items():
        if ticker not in english_words and not (ticker in ignore_words):
            print(f"{ticker} has been found!")
            final_count[ticker] = stats
    print("_________________________________________________________________")
    print("Scan Complete!")

    if not final_count:
        print("No data was collected for that time range.")
        return []
    else:
        return final_count, total_posts

# main processing
def main_rscanner():
    # Main Operation ------------------------------------------------------------------------------------
    # print(date.today().isoformat())
    print("Loaded tickers:", len(tickers))

    Chosen_end_date = pick_time()
    final_count, total_posts = post_scan(Chosen_end_date, tickers)

    print("There is a total of", total_posts, "posts.\n")

    # Add New Column and Sort
    final_count= add_data(final_count)
    sorted_final = sort(final_count, "score")

    return sorted_final

    #
    #
    # # Sort
    #
    # sorted_final2 = sort(final_count, "mentions")
    #
    # # Pandas DF
    # df1 = pd.DataFrame(
    #     [
    #         (ticker, stats["mentions"], stats["bull"], stats["bear"], stats["signal"], stats["interpret"], stats["score"], stats["date"])
    #         for ticker, stats in sorted_final1
    #     ],
    #     columns=["Ticker", "Mentions", "Bull", "Bear", "Signal", "Conclusion", "Score", "Date"]
    # )
    #
    # df2 = pd.DataFrame(
    #     [
    #         (ticker, stats["mentions"], stats["bull"], stats["bear"], stats["signal"], stats["interpret"], stats["score"], stats["date"])
    #         for ticker, stats in sorted_final2
    #     ],
    #     columns=["Ticker", "Mentions", "Bull", "Bear", "Signal", "Conclusion", "Score", "Date"]
    # )
    #
    # print(f"Sorted by Score: \n {df1[:10]} \n")
    # print(f"Sorted by Mentions: \n {df2[:10]}")
    #
    # #--------------------------
    #
    # top_10 = []
    # for ticker, stats in sorted_final1:
    #     top_10.append(ticker)
    # top_10 = top_10[:10]
    #
    # print(top_10)

if __name__ == "__main__":
    main_rscanner()