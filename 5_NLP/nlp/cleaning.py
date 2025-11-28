# nlp/cleaning.py

import re
import nltk
from nltk.corpus import stopwords

stop_words = set(stopwords.words("english"))

def clean_text(text, remove_stopwords=False):
    # Remove non-ASCII junk
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # Remove URLs
    text = re.sub(r"http\S+|www\S+", "", text)

    # Remove emails
    text = re.sub(r"\S+@\S+", "", text)

    # Remove multiple punctuation (!!! → !)
    text = re.sub(r"([!?.,]){2,}", r"\1", text)

    # Remove special characters except .,?! letters and numbers
    text = re.sub(r"[^a-zA-Z0-9\s\.\?\!]", " ", text)

    # Optional stopword removal
    if remove_stopwords:
        tokens = text.split()
        tokens = [t for t in tokens if t not in stop_words]
        text = " ".join(tokens)

    # Remove multiple spaces again
    text = re.sub(r"\s+", " ", text).strip()

    return text
