import os
from dotenv import load_dotenv
from anthropic import Anthropic
import json

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

with open("output_full_text.txt", "r", encoding="utf-8") as file:
    full_text = file.read()

start = full_text.find("CONSOLIDATED STATEMENTS OF OPERATIONS")
income_statement_text = full_text[start:start + 3000]

SYSTEM_PROMPT = """You are a financial data extraction tool.
Extract the income statement table from the text below into structured JSON.
Return a JSON array of objects, each with: line_item, year_2023, year_2024, year_2025.
Return ONLY valid JSON, no markdown fences, no explanation."""

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1500,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": income_statement_text}]
)

raw_text = response.content[0].text.strip()
if raw_text.startswith("```"):
    raw_text = raw_text.split("```")[1]
    if raw_text.startswith("json"):
        raw_text = raw_text[4:]
    raw_text = raw_text.strip()

parsed = json.loads(raw_text)

print(json.dumps(parsed, indent=2))
with open("output/income_statement_llm.json", "w", encoding="utf-8") as file:
    json.dump(parsed, file, indent=4)

print("\nSaved to output/income_statement_llm.json")