import os
import json
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.prompts import PromptTemplate
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

load_dotenv()

# ---------- Config ----------

Settings.llm = Anthropic(model="claude-sonnet-4-5", api_key=os.getenv("ANTHROPIC_API_KEY"))
Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

# ---------- Load ----------

BASE_DIR = os.path.dirname(__file__)
CHUNKS_PATH = os.path.join(BASE_DIR, "..", "rag_pipeline", "chunks.json")

with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
    chunks = json.load(file)

documents = [Document(text=chunk) for chunk in chunks]
print(f"Loaded {len(documents)} documents")

# ---------- Index ----------

index = VectorStoreIndex.from_documents(documents)

# ---------- OVERRIDE: our own grounded prompt (from Ch. 8) ----------

GROUNDED_PROMPT = PromptTemplate(
    """You are a financial analyst assistant. Answer the question using ONLY the
context below, which comes from a company's 10-K filing.

Rules:
- If the answer is not found in the context, say exactly: "Not found in the report."
- Do not guess and do not use outside knowledge.
- Cite the source excerpt for every claim you make.

Context:
---------------------
{context_str}
---------------------

Question: {query_str}
Answer: """
)

query_engine = index.as_query_engine(similarity_top_k=3)
query_engine.update_prompts(
    {"response_synthesizer:text_qa_template": GROUNDED_PROMPT}
)

# ---------- Query ----------

question = "What is Uber's CEO's favorite programming language?"
response = query_engine.query(question)

print(f"\n=== Question: {question} ===")
print(f"Answer: {response}")
print(f"Sources used: {len(response.source_nodes)}")