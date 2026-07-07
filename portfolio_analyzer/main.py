import json
from loader import load_stocks
from analysis import analyze_portfolio

stocks = load_stocks()
results, summary = analyze_portfolio(stocks)

for item in results:
    print(f"{item['ticker']}: {item['verdict']} (P/E {item['pe']})")

print(f"\nSummary: {summary['cheap']} cheap, {summary['fair']} fair, {summary['expensive']} expensive")

report = {
    "results": results,
    "summary": summary
}

with open("report.json", "w") as file:
    json.dump(report, file, indent=4)

print("\nReport saved to report.json")