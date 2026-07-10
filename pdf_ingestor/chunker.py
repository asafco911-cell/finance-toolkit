def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


with open("output_full_text.txt", "r", encoding="utf-8") as file:
    full_text = file.read()

chunks = chunk_text(full_text)

print(f"Total chunks created: {len(chunks)}")
print(f"\n=== First chunk (first 300 characters) ===")
print(chunks[0][:300])

import json
with open("output/chunks.json", "w", encoding="utf-8") as file:
    json.dump(chunks, file, indent=2)

print("\nSaved to output/chunks.json")