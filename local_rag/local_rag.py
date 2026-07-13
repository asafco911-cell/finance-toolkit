import os
import sys
import json
from openai import OpenAI
from pydantic import ValidationError

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "rag_pipeline"))
from rag_pipeline import retrieve, build_user_prompt, SYSTEM_PROMPT, strip_markdown_fence
from validated_answer import ValidatedRAGAnswer

client_local = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)


def generate_answer_local(system_prompt, user_prompt, n_excerpts):
    response = client_local.chat.completions.create(
        model="llama3.2",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    raw_text = response.choices[0].message.content
    cleaned_text = strip_markdown_fence(raw_text)
    data = json.loads(cleaned_text)

    # Validate WITH context: the model may only cite excerpts 1..n_excerpts
    return ValidatedRAGAnswer.model_validate(
        data,
        context={"n_excerpts": n_excerpts}
    )


if __name__ == "__main__":
    question = "What was the revenue growth?"
    n_results = 3

    retrieved_chunks = retrieve(question, n_results=n_results)
    user_prompt = build_user_prompt(question, retrieved_chunks)

    print(f"=== Question: {question} ===")
    print(f"(Sent {len(retrieved_chunks)} excerpts to the model)\n")

    try:
        result = generate_answer_local(SYSTEM_PROMPT, user_prompt, len(retrieved_chunks))

        print("=== Answer (local llama3.2) ===")
        print(f"Found:   {result.found}")
        print(f"Answer:  {result.answer}")
        print(f"Sources: {result.sources}")

    except ValidationError as e:
        print("=== VALIDATION FAILED — model output rejected ===")
        print(e)

    except json.JSONDecodeError as e:
        print("=== JSON PARSE FAILED — model did not return valid JSON ===")
        print(e)

       