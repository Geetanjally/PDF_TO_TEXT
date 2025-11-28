# nlp/sentence_splitter.py

import spacy
from nltk.tokenize import sent_tokenize

try:
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except:
    SPACY_AVAILABLE = False

def split_into_sentences(text):
    if SPACY_AVAILABLE:
        doc = nlp(text)
        return [sent.text.strip() for sent in doc.sents]
    else:
        return sent_tokenize(text)
