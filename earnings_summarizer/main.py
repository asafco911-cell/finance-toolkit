from summarizer import summarize_with_anthropic, summarize_with_openai

with open("earnings_release.txt", "r", encoding="utf-8") as file:
    earnings_text = file.read()

# Anthropic
claude_summary, claude_input, claude_output = summarize_with_anthropic(earnings_text)

# OpenAI
gpt_summary, gpt_input, gpt_output = summarize_with_openai(earnings_text)

print("=" * 60)
print("CLAUDE (Anthropic) SUMMARY")
print("=" * 60)
print(claude_summary)
print(f"\nTokens — Input: {claude_input}, Output: {claude_output}")

print("\n" + "=" * 60)
print("GPT-4o (OpenAI) SUMMARY")
print("=" * 60)
print(gpt_summary)
print(f"\nTokens — Input: {gpt_input}, Output: {gpt_output}")

# עלויות משוערות
claude_cost = (claude_input / 1_000_000) * 3 + (claude_output / 1_000_000) * 15
gpt_cost = (gpt_input / 1_000_000) * 2.5 + (gpt_output / 1_000_000) * 10

print("\n" + "=" * 60)
print("COST COMPARISON (estimated)")
print("=" * 60)
print(f"Claude: ${claude_cost:.4f}")
print(f"GPT-4o: ${gpt_cost:.4f}")
