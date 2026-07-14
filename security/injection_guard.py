import re

# Patterns that have no legitimate place in a financial question
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+the\s+above",
    r"disregard\s+(all\s+)?(previous|prior)",
    r"forget\s+(everything|all|your)\s+",
    r"you\s+are\s+now\s+",
    r"new\s+instructions?\s*:",
    r"system\s*prompt",
    r"debug\s+mode",
    r"developer\s+mode",
    r"reveal\s+your\s+(instructions|prompt|rules)",
    r"print\s+your\s+(instructions|prompt|system)",
]


class InjectionAttemptError(Exception):
    """Raised when input appears to contain a prompt-injection attempt."""
    pass


def scan_for_injection(text, source="input"):
    lowered = text.lower()

    for pattern in INJECTION_PATTERNS:
        match = re.search(pattern, lowered)
        if match:
            raise InjectionAttemptError(
                f"Possible prompt injection detected in {source}: "
                f"matched pattern '{pattern}' at '{match.group()}'"
            )

    return text

def sanitize_chunks(chunks):
    """Scan retrieved chunks. Drop any that appear to contain injected instructions."""
    safe_chunks = []
    dropped = 0

    for i, chunk in enumerate(chunks):
        try:
            scan_for_injection(chunk, source=f"retrieved chunk {i + 1}")
            safe_chunks.append(chunk)
        except InjectionAttemptError as e:
            print(f"[SECURITY] Dropped chunk {i + 1}: {e}")
            dropped += 1

    if dropped:
        print(f"[SECURITY] {dropped} chunk(s) removed before reaching the LLM.")

    return safe_chunks