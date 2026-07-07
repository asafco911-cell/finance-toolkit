def classify(pe):
    if pe < 15:
        return "Cheap"
    elif pe < 30:
        return "Fair"
    else:
        return "Expensive"

def analyze_portfolio(stocks):
    results = []
    cheap_count = 0
    fair_count = 0
    expensive_count = 0

    for stock in stocks:
        result = classify(stock["pe"])
        results.append({"ticker": stock["ticker"], "pe": stock["pe"], "verdict": result})

        if result == "Cheap":
            cheap_count += 1
        elif result == "Fair":
            fair_count += 1
        else:
            expensive_count += 1

    summary = {
        "cheap": cheap_count,
        "fair": fair_count,
        "expensive": expensive_count
    }

    return results, summary