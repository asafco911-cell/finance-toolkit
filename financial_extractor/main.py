from extractor import extract_earnings_data

report_files = ["report1_panw.txt", "report2_camt.txt", "report3_amzn.txt"]

total_input_tokens = 0
total_output_tokens = 0

for filename in report_files:
    print("=" * 60)
    print(f"Processing: {filename}")
    print("=" * 60)

    with open(filename, "r", encoding="utf-8") as file:
        report_text = file.read()

    result, input_tokens, output_tokens = extract_earnings_data(report_text)

    total_input_tokens += input_tokens
    total_output_tokens += output_tokens

    if result is not None:
        print(f"Revenue: ${result.revenue:,.0f}")
        print(f"Net Income: ${result.net_income:,.0f}")
        print(f"EPS: ${result.eps}")
        print(f"Guidance: {result.guidance}")
        print(f"Tokens — Input: {input_tokens}, Output: {output_tokens}")
    else:
        print(f"Skipping {filename} — extraction failed.")
        print(f"Tokens — Input: {input_tokens}, Output: {output_tokens}")

    print()

print("=" * 60)
print("TOTAL TOKEN USAGE")
print("=" * 60)
print(f"Total input tokens: {total_input_tokens}")
print(f"Total output tokens: {total_output_tokens}")

total_cost = (total_input_tokens / 1_000_000) * 3 + (total_output_tokens / 1_000_000) * 15
print(f"Estimated total cost: ${total_cost:.4f}")