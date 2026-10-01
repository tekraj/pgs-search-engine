import os
import logging
import joblib
import pandas as pd


# ============================================================
# Logging Configuration
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


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

    logger.error(
        f"LightGBM model not found: {MODEL_PATH}"
    )

    raise FileNotFoundError(
        f"LightGBM model not found:\n{MODEL_PATH}\n\n"
        "Please copy lightgbm_reranker.pkl into the tests folder."
    )

model = joblib.load(MODEL_PATH)

logger.info("LightGBM model loaded successfully.")


# ============================================================
# Prepare Features
# ============================================================

def prepare_features(results):

    """
    Prepare search result features for LightGBM prediction.

    Missing features are assigned a default value of 0.
    Non-numeric values are converted to numeric values.
    Invalid values are replaced with 0.
    """

    logger.info(
        f"Preparing features for {len(results)} results."
    )

    df = pd.DataFrame(results)

    # --------------------------------------------------------
    # Add missing features
    # --------------------------------------------------------

    missing_features = []

    for feature in FEATURES:

        if feature not in df.columns:

            df[feature] = 0
            missing_features.append(feature)

    if missing_features:

        logger.warning(
            f"Missing features added with default value 0: "
            f"{missing_features}"
        )


    # --------------------------------------------------------
    # Convert features to numeric
    # --------------------------------------------------------

    for feature in FEATURES:

        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce"
        )


    # --------------------------------------------------------
    # Replace missing or invalid values
    # --------------------------------------------------------

    invalid_values = df[FEATURES].isna().sum().sum()

    if invalid_values > 0:

        logger.warning(
            f"{invalid_values} missing or invalid feature values "
            "were replaced with 0."
        )

    df[FEATURES] = df[FEATURES].fillna(0)

    logger.info("Feature preparation completed.")

    return df


# ============================================================
# Re-ranking Function
# ============================================================

def rerank_results(results, top_k=10):

    """
    Re-rank search results using the trained LightGBM model.

    Parameters
    ----------
    results : list
        Search results containing ranking features.

    top_k : int
        Number of results to return.

    Returns
    -------
    list
        Re-ranked search results.
    """

    logger.info("Starting LightGBM re-ranking process.")


    # --------------------------------------------------------
    # Validate results
    # --------------------------------------------------------

    if not isinstance(results, list):

        logger.error(
            "Invalid results type. Expected a list."
        )

        raise TypeError(
            "results must be provided as a list."
        )


    if not results:

        logger.warning(
            "No search results provided."
        )

        return []


    logger.info(
        f"Received {len(results)} search results."
    )


    # --------------------------------------------------------
    # Validate top_k
    # --------------------------------------------------------

    if not isinstance(top_k, int) or top_k <= 0:

        logger.error(
            f"Invalid top_k value: {top_k}"
        )

        raise ValueError(
            "top_k must be a positive integer."
        )


    # --------------------------------------------------------
    # Prepare features
    # --------------------------------------------------------

    df = prepare_features(results)


    # --------------------------------------------------------
    # Store input ranking
    # --------------------------------------------------------

    df["original_rank"] = range(
        1,
        len(df) + 1
    )


    # --------------------------------------------------------
    # Remove duplicate documents
    # --------------------------------------------------------

    original_count = len(df)

    if "id" in df.columns:

        df = df.drop_duplicates(
            subset=["id"],
            keep="first"
        )

    duplicate_count = original_count - len(df)

    if duplicate_count > 0:

        logger.warning(
            f"Removed {duplicate_count} duplicate result(s)."
        )

    else:

        logger.info(
            "No duplicate results found."
        )


    logger.info(
        f"Results after duplicate removal: {len(df)}"
    )


    # --------------------------------------------------------
    # Generate LightGBM prediction
    # --------------------------------------------------------

    logger.info(
        "Generating LightGBM ranking scores."
    )

    df["rerank_score"] = model.predict(
        df[FEATURES]
    )


    # --------------------------------------------------------
    # Handle invalid prediction scores
    # --------------------------------------------------------

    df["rerank_score"] = pd.to_numeric(
        df["rerank_score"],
        errors="coerce"
    )

    invalid_scores = df["rerank_score"].isna().sum()

    if invalid_scores > 0:

        logger.warning(
            f"{invalid_scores} invalid prediction score(s) "
            "were replaced with 0."
        )

    df["rerank_score"] = df[
        "rerank_score"
    ].fillna(0)


    # --------------------------------------------------------
    # Sort by LightGBM score
    # --------------------------------------------------------

    df = df.sort_values(
        by="rerank_score",
        ascending=False
    )


    logger.info(
        "Results sorted by LightGBM ranking score."
    )


    # --------------------------------------------------------
    # Assign new ranking
    # --------------------------------------------------------

    df["new_rank"] = range(
        1,
        len(df) + 1
    )


    # --------------------------------------------------------
    # Calculate rank change
    # --------------------------------------------------------

    df["rank_change"] = (
        df["original_rank"] - df["new_rank"]
    )


    # --------------------------------------------------------
    # Return Top K results
    # --------------------------------------------------------

    final_results = df.head(
        top_k
    ).to_dict(
        orient="records"
    )


    logger.info(
        f"Returning top {len(final_results)} results."
    )

    logger.info(
        "LightGBM re-ranking completed successfully."
    )

    return final_results


# ============================================================
# Test the Re-ranker
# ============================================================

if __name__ == "__main__":

    print("\nTesting LightGBM re-ranker...")
    print("-" * 100)


    sample_results = [

        {
            "id": 1,
            "title": "Kathmandu Tourism",
            "content": (
                "Information about tourism "
                "in Kathmandu Nepal."
            ),

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
            "content": (
                "Information about travelling "
                "around Nepal."
            ),

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
            "content": (
                "Latest news and information "
                "from Nepal."
            ),

            "bm25_score": 5.1,
            "vector_score": 0.72,
            "title_match": 0,
            "geo_match": 1,
            "freshness": 0.95,
            "source_authority": 0.85,
            "language_match": 1,
            "query_term_ratio": 0.4,
            "content_length": 400
        },

        {
            "id": 4,
            "title": "Nepal Travel Guide",
            "content": (
                "Complete guide for travelling "
                "and tourism in Nepal."
            ),

            "bm25_score": 7.8,
            "vector_score": 0.88,
            "title_match": 1,
            "geo_match": 1,
            "freshness": 0.9,
            "source_authority": 0.95,
            "language_match": 1,
            "query_term_ratio": 0.8,
            "content_length": 600
        },

        # ----------------------------------------------------
        # Test missing feature handling
        # ----------------------------------------------------

        {
            "id": 5,
            "title": "Nepal Travel Information",
            "content": (
                "General travel information "
                "about Nepal."
            ),

            "bm25_score": 5.9,
            "vector_score": 0.78,
            "title_match": 1,
            "geo_match": 1,
            "freshness": 0.75,
            "source_authority": 0.80,
            "language_match": 1,
            "query_term_ratio": 0.6

            # content_length intentionally missing
        }

    ]


    # ========================================================
    # Run re-ranking
    # ========================================================

    results = rerank_results(
        sample_results,
        top_k=10
    )


    # ========================================================
    # Display Results
    # ========================================================

    print("\nRe-ranked results:")
    print("-" * 100)


    for result in results:

        print(
            f"New Rank: {result.get('new_rank')} | "
            f"Original Rank: {result.get('original_rank')} | "
            f"Rank Change: {result.get('rank_change')} | "
            f"ID: {result.get('id')} | "
            f"Title: {result.get('title')} | "
            f"Score: {result.get('rerank_score', 0):.6f}"
        )


    print("-" * 100)


    # ========================================================
    # Prediction Summary
    # ========================================================

    if results:

        scores = [
            result["rerank_score"]
            for result in results
        ]


        print(
            f"Highest rerank score: "
            f"{max(scores):.6f}"
        )

        print(
            f"Lowest rerank score: "
            f"{min(scores):.6f}"
        )

        print(
            f"Average rerank score: "
            f"{sum(scores) / len(scores):.6f}"
        )


        # ----------------------------------------------------
        # Rank movement analysis
        # ----------------------------------------------------

        improved = sum(
            1
            for result in results
            if result["rank_change"] > 0
        )

        unchanged = sum(
            1
            for result in results
            if result["rank_change"] == 0
        )

        moved_down = sum(
            1
            for result in results
            if result["rank_change"] < 0
        )


        print(
            f"Results improved: {improved}"
        )

        print(
            f"Results unchanged: {unchanged}"
        )

        print(
            f"Results moved down: {moved_down}"
        )


    print(
        f"Total results returned: {len(results)}"
    )

    print(
        "Re-ranking completed successfully."
    )