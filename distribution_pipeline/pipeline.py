import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "rag_pipeline"))
from rag_pipeline import retrieve, build_user_prompt, generate_answer, SYSTEM_PROMPT

from translator import translate_to_hebrew
from whatsapp_sender import send_whatsapp


def run_distribution(question, to_number=None):
    # --- Stage 1: Analyze (RAG) ---
    print(f"[1/4] Analyzing: {question}")

    retrieved_chunks = retrieve(question, n_results=3)
    user_prompt = build_user_prompt(question, retrieved_chunks)
    result = generate_answer(SYSTEM_PROMPT, user_prompt)

    if not result.found:
        print("[!] Answer not found in the report. Nothing to distribute.")
        return None

    print(f"[2/4] Answer (EN): {result.answer}")

    # --- Stage 2: Translate ---
    hebrew_answer = translate_to_hebrew(result.answer)
    print(f"[3/4] Translated to Hebrew.")

    # --- Stage 3: Format the message ---
    message = (
        f"📊 ניתוח דוח\n\n"
        f"שאלה: {question}\n\n"
        f"{hebrew_answer}\n\n"
        f"מקורות: קטעים {result.sources}"
    )

    # --- Stage 4: Distribute ---
    sid = send_whatsapp(message, to_number)
    print(f"[4/4] Sent to WhatsApp. SID: {sid}")

    return message


if __name__ == "__main__":
    run_distribution("What was the revenue growth?")