import os
import joblib
import pandas as pd


# ============================================================
# LightGBM Model Configuration
# ============================================================

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "lightgbm_reranker.pkl"
)


FEATURES = [
    "bm25_score",
    "vector_score",
    "title_match",
    "geo_match",
    "freshness",
    "source_authority",
    "language_match",
    "query_term_ratio",
    "content_length"
]


# ============================================================
# Load LightGBM Model
# ============================================================

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"LightGBM model not found:\n{MODEL_PATH}\n\n"
        "Please copy lightgbm_reranker.pkl into the tests folder."
    )

model = joblib.load(MODEL_PATH)

print("LightGBM model loaded successfully.")


# ============================================================
# Re-ranking Function
# ============================================================

def rerank_results(results, top_k=10):

    """
    Re-rank search results using the trained LightGBM model.

    Parameters
    ----------
    results : list
        Search results containing the LightGBM features.

    top_k : int
        Number of results to return.

    Returns
    -------
    list
        Re-ranked search results.
    """

    # No results
    if not results:
        return []


    # Convert search results into DataFrame
    df = pd.DataFrame(results)


    # ========================================================
    # Make sure all required features exist
    # ========================================================

    for feature in FEATURES:

        if feature not in df.columns:
            df[feature] = 0


    # ========================================================
    # Convert feature values to numeric
    # ========================================================

    for feature in FEATURES:

        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce"
        )


    # ========================================================
    # Handle missing values
    # ========================================================

    df[FEATURES] = df[FEATURES].fillna(0)


    # ========================================================
    # LightGBM Prediction
    # ========================================================

    df["rerank_score"] = model.predict(
        df[FEATURES]
    )


    # ========================================================
    # Sort by LightGBM score
    # ========================================================

    df = df.sort_values(
        "rerank_score",
        ascending=False
    )


    # ========================================================
    # Return Top K Results
    # ========================================================

    return df.head(top_k).to_dict(
        orient="records"
    )


# ============================================================
# Test the Re-ranker
# ============================================================

if __name__ == "__main__":

    print("\nTesting LightGBM re-ranker...")


    sample_results = [

        {
            "id": 1,
            "title": "Kathmandu Tourism",
            "content": "Information about tourism in Kathmandu Nepal.",

            "bm25_score": 8.5,
            "vector_score": 0.91,
            "title_match": 1,
            "geo_match": 1,
            "freshness": 0.8,
            "source_authority": 0.9,
            "language_match": 1,
            "query_term_ratio": 0.7,
            "content_length": 500
        },

        {
            "id": 2,
            "title": "Travel in Nepal",
            "content": "Information about travelling around Nepal.",

            "bm25_score": 6.2,
            "vector_score": 0.85,
            "title_match": 0,
            "geo_match": 1,
            "freshness": 0.7,
            "source_authority": 0.8,
            "language_match": 1,
            "query_term_ratio": 0.5,
            "content_length": 700
        },

        {
            "id": 3,
            "title": "Nepal News",
            "content": "Latest news and information from Nepal.",

            "bm25_score": 5.1,
            "vector_score": 0.72,
            "title_match": 0,
            "geo_match": 1,
            "freshness": 0.95,
            "source_authority": 0.85,
            "language_match": 1,
            "query_term_ratio": 0.4,
            "content_length": 400
        }

    ]


    # Run re-ranking
    results = rerank_results(
        sample_results,
        top_k=10
    )


    # ========================================================
    # Display Results
    # ========================================================

    print("\nRe-ranked results:")
    print("-" * 60)


    for rank, result in enumerate(
        results,
        start=1
    ):

        print(
            f"Rank {rank} | "
            f"ID: {result.get('id')} | "
            f"Title: {result.get('title')} | "
            f"Score: {result['rerank_score']:.4f}"
        )


    print("-" * 60)
    print("Re-ranking completed successfully.")