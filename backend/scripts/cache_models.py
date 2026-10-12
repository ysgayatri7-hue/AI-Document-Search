"""Download the public retrieval models into the configured Hugging Face cache."""
import os

from sentence_transformers import CrossEncoder, SentenceTransformer


embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
reranker_model = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

print(f"Caching embedding model: {embedding_model}")
SentenceTransformer(embedding_model)
print(f"Caching cross-encoder: {reranker_model}")
CrossEncoder(reranker_model)
print("Retrieval model cache is ready.")
