import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "rag_pipeline"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "security"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "distribution_pipeline"))

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv
import deepl

from rag_pipeline import secure_retrieve, build_user_prompt, generate_answer, SYSTEM_PROMPT
from injection_guard import scan_for_injection, InjectionAttemptError
from whatsapp_sender import send_whatsapp

load_dotenv()

app = FastAPI()

validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))
translator = deepl.Translator(os.getenv("DEEPL_API_KEY"))

ALLOWED_NUMBERS = {os.getenv("MY_WHATSAPP_NUMBER")}


@app.get("/health")
def health_check():
    return {"status": "ok"}


async def verify_twilio_signature(request: Request, form_data: dict):
    """Layer 1: cryptographic proof the request actually came from Twilio."""
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)

    if not validator.validate(url, form_data, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature.")


def process_question(hebrew_question: str, sender: str):
    """Runs in the background: translate → RAG → translate → reply."""
    try:
         # Layer 0: scan the raw input BEFORE translation
        scan_for_injection(hebrew_question, source="raw WhatsApp message")
        # 1. Hebrew → English
        english_question = translator.translate_text(
            hebrew_question, target_lang="EN-US"
        ).text
        print(f"[1/4] Translated to EN: {english_question}")

        # 2. RAG (with injection guard baked in)
        chunks = secure_retrieve(english_question, n_results=3)
        user_prompt = build_user_prompt(english_question, chunks)
        result = generate_answer(SYSTEM_PROMPT, user_prompt)
        print(f"[2/4] found={result.found}")

        # 3. English → Hebrew
        hebrew_answer = translator.translate_text(
            result.answer, target_lang="HE"
        ).text
        print(f"[3/4] Translated to HE.")

        # 4. Reply
        if result.found:
            reply = f"📊 {hebrew_answer}\n\nמקורות: קטעים {result.sources}"
        else:
            reply = f"⚠️ לא נמצא בדוח.\n\n{hebrew_answer}"

        send_whatsapp(reply, sender)
        print(f"[4/4] Replied to {sender}")

    except InjectionAttemptError as e:
        print(f"[SECURITY] Injection attempt from {sender}: {e}")
        send_whatsapp("⚠️ הבקשה נדחתה מטעמי אבטחה.", sender)

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        send_whatsapp("⚠️ אירעה שגיאה בעיבוד הבקשה. נסה שוב.", sender)


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    form_data = dict(form)

    # --- Layer 1: is this really from Twilio? ---
    await verify_twilio_signature(request, form_data)

    # --- Layer 2: now we can trust 'From'. Is it an allowed number? ---
    sender = form_data.get("From", "")
    if sender not in ALLOWED_NUMBERS:
        print(f"[SECURITY] Rejected message from unauthorized number: {sender}")
        raise HTTPException(status_code=403, detail="Unauthorized sender.")

    question = form_data.get("Body", "").strip()
    print(f"\n=== Incoming from {sender}: {question} ===")

    if not question:
        return PlainTextResponse("", status_code=204)

    # Respond to Twilio immediately; do the work in the background
    background_tasks.add_task(process_question, question, sender)

    return PlainTextResponse("", status_code=204)