# nlp/prepare.py

from .normalize import normalize_text
from .cleaning import clean_text
from .sentence_splitter import split_into_sentences

def prepare_text(raw_text):
    # Step 1 — Normalize
    normalized = normalize_text(raw_text)

    # Step 2 — Deep clean
    cleaned = clean_text(normalized)

    # Step 3 — Sentence splitting
    sentences = split_into_sentences(cleaned)

    return {
        "clean_text": cleaned,
        "sentences": sentences
    }
