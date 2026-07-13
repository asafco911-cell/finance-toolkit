import os
from dotenv import load_dotenv
import deepl

load_dotenv()

translator = deepl.Translator(os.getenv("DEEPL_API_KEY"))


def translate_to_hebrew(text):
    result = translator.translate_text(text, target_lang="HE")
    return result.text


if __name__ == "__main__":
    sample = "Revenue grew 18% year-over-year, increasing from $43,978 million to $52,017 million."
    translated = translate_to_hebrew(sample)

    print("=== Original ===")
    print(sample)
    print("\n=== Hebrew ===")
    print(translated)
    