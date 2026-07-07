import json

with open("stocks.json", "r") as file:
    loaded_stocks = json.load(file)

#print(loaded_stocks)
#try:
 #   with open("stocks.json", "r") as file:
  #      loaded_stocks = json.load(file)
   # print("loaded existing stocks!")
#except FileNotFoundError:
 #   print("stocks.json not found — starting fresh.")
  #  loaded_stocks = []

#loaded_stocks.append({"ticker": "msft", "pe": 35})

#with open("stocks.json", "w") as file:
   # json.dump(loaded_stocks, file)

#print(f"Total stocks now: {len(loaded_stocks)}")

new_ticker = "MSFT"
new_pe = 35

existing_tickers = []
for stock in loaded_stocks:
    existing_tickers.append(stock["ticker"])

if new_ticker not in existing_tickers:
    loaded_stocks.append({"ticker": new_ticker, "pe": new_pe})
    print(f"{new_ticker} added.")
else:
    print(f"{new_ticker} already exists — skipping.")

import json

with open("stocks.json", "r") as file:
    loaded_stocks = json.load(file)

seen_tickers = []
unique_stocks = []

for stock in loaded_stocks:
    if stock["ticker"] not in seen_tickers:
        seen_tickers.append(stock["ticker"])
        unique_stocks.append(stock)

with open("stocks.json", "w") as file:
    json.dump(unique_stocks, file)

print(f"Cleaned! {len(loaded_stocks)} → {len(unique_stocks)} stocks")