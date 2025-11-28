# summarizer_extractive.py

from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------
# Load SBERT model once (fast)
# ---------------------------------------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")  # lightweight, accurate


# ---------------------------------------------------------
# Compute embeddings
# ---------------------------------------------------------
def embed_sentences(sentences):
    return model.encode(sentences)


# ---------------------------------------------------------
# Rank sentences by "importance"
# method: cosine similarity centrality (TextRank-like)
# ---------------------------------------------------------
def rank_sentences(sentences, top_k=5):
    if len(sentences) == 0:
        return []

    embeddings = embed_sentences(sentences)

    sim_matrix = cosine_similarity(embeddings)

    scores = sim_matrix.sum(axis=1)

    ranked_ids = np.argsort(scores)[::-1][:top_k]

    ranked_sentences = [sentences[i] for i in ranked_ids]

    return ranked_sentences
