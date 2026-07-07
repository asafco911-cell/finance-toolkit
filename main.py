from storage import load_stocks, save_stocks

stocks = load_stocks()
print(f"Loaded {len(stocks)} stocks")

stocks.append({"ticker": "MSFT", "pe": 35})

save_stocks(stocks)
print(f"Saved {len(stocks)} stocks")