import json
import chromadb

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

question = "What was the revenue growth?"

results = collection.query(
    query_texts=[question],
    n_results=10
)

print(f"\n=== Question: {question} ===\n")

for i, chunk in enumerate(results["documents"][0]):
    print(f"--- Result {i + 1} ---")
    print(chunk[:400])
    print()