import os
from dotenv import load_dotenv
from anthropic import Anthropic
from openai import OpenAI

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a careful financial analyst. Summarize the earnings release in exactly 5 bullet points:
1. Revenue
2. Profit/Earnings
3. Surprises (vs expectations)
4. Risks mentioned
5. Management tone"""

def summarize_with_anthropic(text):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": text}
        ]
    )

    summary = response.content[0].text
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    return summary, input_tokens, output_tokens

# now with OPEN AI Model

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize_with_openai(text):
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
    )

    summary = response.choices[0].message.content
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    return summary, input_tokens, output_tokens
