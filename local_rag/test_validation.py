"""
Sanity checks for ValidatedRAGAnswer.

A safety net you haven't tested is not a safety net — it's hope.
These tests verify that the validator rejects hallucinated and ungrounded output.
"""

from pydantic import ValidationError
from validated_answer import ValidatedRAGAnswer

N_EXCERPTS = 3


def check(name, data, should_pass):
    try:
        ValidatedRAGAnswer.model_validate(data, context={"n_excerpts": N_EXCERPTS})
        passed = True
        error = None
    except ValidationError as e:
        passed = False
        error = e

    ok = (passed == should_pass)
    status = "PASS" if ok else "FAIL"

    print(f"[{status}] {name}")
    if not ok:
        print(f"        Expected {'accept' if should_pass else 'reject'}, got the opposite.")
    if error and not should_pass:
        print(f"        Correctly rejected: {error.errors()[0]['msg']}")
    print()


if __name__ == "__main__":
    print(f"=== Validating against {N_EXCERPTS} provided excerpts ===\n")

    check(
        "Valid answer with real sources",
        {"found": True, "answer": "Revenue grew 18%", "sources": [1, 2]},
        should_pass=True
    )

    check(
        "Hallucinated source (Excerpt 5 of 3)",
        {"found": True, "answer": "Revenue grew 18%", "sources": [5]},
        should_pass=False
    )

    check(
        "Hallucinated source mixed with a real one",
        {"found": True, "answer": "Revenue grew 18%", "sources": [53, 2]},
        should_pass=False
    )

    check(
        "Claims found=True but cites no sources",
        {"found": True, "answer": "Revenue grew 18%", "sources": []},
        should_pass=False
    )

    check(
        "Honest refusal: found=False, no sources",
        {"found": False, "answer": "Not found in the report.", "sources": []},
        should_pass=True
    )