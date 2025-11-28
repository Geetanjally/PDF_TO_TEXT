# nlp/normalize.py

import re
import unicodedata

def normalize_text(text):
    # 1. Normalize unicode
    text = unicodedata.normalize("NFKC", text)

    # 2. Lowercase
    text = text.lower()

    # 3. Fix hyphenated words split across lines: "inform-\nation"
    text = re.sub(r"-\s*\n\s*", "", text)

    # 4. Remove multiple newlines → \n\n → \n
    text = re.sub(r"\n\s*\n+", "\n", text)

    # 5. Remove unwanted symbols from OCR
    text = re.sub(r"[•◦·▪▶►✓✔~]", "", text)

    # 6. Replace weird multiple spaces
    text = re.sub(r"\s+", " ", text)

    # 7. Trim spaces
    return text.strip()
