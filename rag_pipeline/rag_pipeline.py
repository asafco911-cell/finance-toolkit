import os
import json
import chromadb
from dotenv import load_dotenv
from anthropic import Anthropic
from schema import RAGAnswer

# ---------- Setup ----------

load_dotenv()
client_anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

with open("chunks.json", "r", encoding="utf-8") as file:
    chunks = json.load(file)

print(f"Loaded {len(chunks)} chunks")

client = chromadb.Client()
collection = client.create_collection(name="uber_10k")

chunk_ids = [f"chunk_{i}" for i in range(len(chunks))]

collection.add(
    documents=chunks,
    ids=chunk_ids
)

print(f"Added {len(chunks)} chunks to the vector database")


# ---------- Retrieve ----------

def retrieve(question, n_results=3):
    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )
    return results["documents"][0]


# ---------- Augment ----------

SYSTEM_PROMPT = """You are a financial analyst assistant. Answer the user's question using ONLY the context excerpts provided below, which come from a company's 10-K filing.

Rules:
- If the answer is not found in the excerpts, set "found" to false and briefly explain why in "answer".
- For every claim you make, track which excerpt numbers support it in the "sources" list.
- Respond with ONLY a JSON object matching this structure, no markdown fences, no extra text:
{"found": true/false, "answer": "...", "sources": [1, 2]}"""


def build_user_prompt(question, retrieved_chunks):
    excerpts = "\n\n".join(
        f"[Excerpt {i + 1}]\n{chunk}" for i, chunk in enumerate(retrieved_chunks)
    )
    return f"""Context excerpts from the 10-K:

{excerpts}

Question: {question}"""


# ---------- Generate ----------

def strip_markdown_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def generate_answer(system_prompt, user_prompt):
    response = client_anthropic.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    raw_text = response.content[0].text
    cleaned_text = strip_markdown_fence(raw_text)
    data = json.loads(cleaned_text)
    return RAGAnswer(**data)


# ---------- Run ----------

question = "What was the revenue growth?"
retrieved_chunks = retrieve(question, n_results=3)
user_prompt = build_user_prompt(question, retrieved_chunks)

result = generate_answer(SYSTEM_PROMPT, user_prompt)

print(f"\n=== Question: {question} ===")
print(f"Found: {result.found}")
print(f"Answer: {result.answer}")
print(f"Sources: {result.sources}")