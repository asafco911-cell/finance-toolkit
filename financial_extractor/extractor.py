import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from pydantic import ValidationError
from schema import EarningsData

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a financial data extraction tool.
Extract exactly these 4 fields from the earnings report: revenue, net_income, eps, guidance.

CRITICAL RULES:
- Return ONLY the raw JSON object, starting with { and ending with }
- Do NOT wrap it in markdown code fences (no ```json or ```)
- Do NOT include any explanation text before or after
- revenue and net_income must be plain numbers in USD (e.g. 121700000, NOT "121.7 million")
- eps must be a plain decimal number (e.g. 0.63)
- guidance must always be a string — if no guidance is mentioned, use the string "not mentioned" (never null)"""

def extract_earnings_data(text):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}]
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    raw_text = response.content[0].text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        raw_json = json.loads(raw_text)
        validated = EarningsData(**raw_json)
        return validated, input_tokens, output_tokens
    except json.JSONDecodeError:
        print("Error: Model did not return valid JSON.")
        print(f"Raw response was: {raw_text}")
        return None, input_tokens, output_tokens
    except ValidationError as e:
        print(f"Error: JSON structure doesn't match expected schema.\n{e}")
        return None, input_tokens, output_tokens
    
    