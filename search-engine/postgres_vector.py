import os
from typing import Any

import psycopg2

from dotenv import load_dotenv

from embedding import generate_embedding


load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def vector_search_postgres(
    query: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    query_embedding = generate_embedding(query)
    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        SELECT
            document_id,
            1 - (embedding <=> %s::vector)
                AS vector_score
        FROM documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """

    cursor.execute(
        sql,
        (
            query_embedding,
            query_embedding,
            top_k,
        ),
    )

    rows = cursor.fetchall()
    results: list[dict[str, Any]] = []

    for rank, row in enumerate(rows, start=1):
        results.append(
            {
                "document_id": row[0],
                "vector_score": float(row[1]),
                "rank": rank,
            }
        )

    cursor.close()
    connection.close()

    return results