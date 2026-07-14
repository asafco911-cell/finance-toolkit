import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"Key loaded: {api_key is not None}")

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"Key loaded: {api_key is not None}")

client = Anthropic(api_key=api_key)

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=200,
    system="You are a concise financial analyst assistant.",
    messages=[
        {"role": "user", "content": "Tell me one sentence about the importance of risk management in investing."}
    ]
)

print(response.content[0].text)
