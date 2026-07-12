import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "rag_pipeline"))

from fastapi import FastAPI
from pydantic import BaseModel
from rag_pipeline import retrieve, build_user_prompt, generate_answer, SYSTEM_PROMPT
from schema import RAGAnswer

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


class AskRequest(BaseModel):
    question: str


@app.post("/ask", response_model=RAGAnswer)
def ask(request: AskRequest):
    retrieved_chunks = retrieve(request.question, n_results=3)
    user_prompt = build_user_prompt(request.question, retrieved_chunks)
    result = generate_answer(SYSTEM_PROMPT, user_prompt)
    return result
