stocks = [ 
    {"ticker": "AAPL", "pe": 28},
    {"ticker": "NVDA", "pe": 45},
    {"ticker": "KO", "pe": 12},
    {"ticker": "TSLA","pe": 60},
    {"ticker": "PGR", "pe": 12},
    {"ticker": "FOUR", "pe": 38},
    {"ticker": "AMD", "pe": 97},
    {"ticker": "CAMT","pe": 133},
    {"ticker": "CRM", "pe": 18},
    {"ticker": "MELI","pe": 21},
    {"ticker": "ADBE","pe": 11},
    {"ticker": "MSFT", "pe": 23}
]
def classify (pe):
    if pe < 15:
        return "cheap"
    elif pe <  30:
        return "fair"
    else:
        return "expensive"
    
cheap_count = 0
fair_count = 0
expensive_count = 0

for stock in stocks: 
    result = classify(stock["pe"])
    print(f"{stock["ticker"]} is {result} with P/E of {stock["pe"]}") 
    if result == "cheap":
        cheap_count += 1
    elif result == "fair":
        fair_count += 1
    else:
        expensive_count += 1
    
print(f"\nSummary: {cheap_count} cheap, {fair_count} fair, {expensive_count} expensive")