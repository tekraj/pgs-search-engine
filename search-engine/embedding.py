from sentence_transformers import SentenceTransformer
import os

from dotenv import load_dotenv

load_dotenv()


MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "paraphrase-multilingual-MiniLM-L12-v2"
)


model = SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> list[float]:

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()