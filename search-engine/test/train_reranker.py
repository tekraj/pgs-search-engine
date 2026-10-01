from pathlib import Path

import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import ndcg_score


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = PROJECT_ROOT / "test"

DATA_PATH = TEST_DIR / "ranking_traning_data.csv"
MODEL_PATH = TEST_DIR / "lightgbm_reranker.pkl"
IMPORTANCE_PATH = TEST_DIR / "feature_importance.csv"
RESULTS_PATH = TEST_DIR / "reranked_results.csv"


# Load the training data
print("Loading training data...")

df = pd.read_csv(DATA_PATH)

print("Dataset shape:", df.shape)


# Features used by the ranking model
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

TARGET = "label"


# Check required columns
required_columns = FEATURES + [TARGET, "query"]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"These columns are missing: {missing_columns}"
    )


# Replace missing values with 0
df[FEATURES] = df[FEATURES].fillna(0)
df[TARGET] = df[TARGET].fillna(0)


# Split data based on queries
# Documents from the same query stay in the same dataset.
queries = df["query"].unique()

train_queries, test_queries = train_test_split(
    queries,
    test_size=0.25,
    random_state=42
)

train_df = df[
    df["query"].isin(train_queries)
].copy()

test_df = df[
    df["query"].isin(test_queries)
].copy()


# Sort data by query
train_df = train_df.sort_values("query")
test_df = test_df.sort_values("query")


print("Training rows:", len(train_df))
print("Testing rows:", len(test_df))


# Select features and target
X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]


# Find number of documents for each query
train_groups = (
    train_df
    .groupby("query", sort=False)
    .size()
    .tolist()
)

test_groups = (
    test_df
    .groupby("query", sort=False)
    .size()
    .tolist()
)


print("Training groups:", train_groups)
print("Testing groups:", test_groups)


# Create LightGBM ranking model
model = lgb.LGBMRanker(
    objective="lambdarank",
    metric="ndcg",
    ndcg_at=[5, 10],
    learning_rate=0.05,
    n_estimators=300,
    num_leaves=31,
    random_state=42,
    verbosity=-1
)


# Train the model
print("\nTraining LightGBM model...")

model.fit(
    X_train,
    y_train,
    group=train_groups,
    eval_set=[(X_test, y_test)],
    eval_group=[test_groups],
    callbacks=[
        lgb.early_stopping(
            stopping_rounds=30,
            verbose=True
        )
    ]
)

print("Training completed.")


# Predict ranking scores
test_df["rerank_score"] = model.predict(X_test)


# Calculate NDCG@5
scores = []

for query, group in test_df.groupby("query"):

    if len(group) < 2:
        continue

    actual = group["label"].values
    predicted = group["rerank_score"].values

    score = ndcg_score(
        [actual],
        [predicted],
        k=min(5, len(group))
    )

    scores.append(score)


# Calculate average NDCG
if scores:
    average_ndcg = np.mean(scores)

    print(
        f"\nAverage NDCG@5: {average_ndcg:.4f}"
    )

    print(
        "Number of queries evaluated:",
        len(scores)
    )
else:
    print("\nNo queries available for NDCG evaluation.")


# Feature importance
importance = pd.DataFrame({
    "feature": FEATURES,
    "importance": model.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

print("\nFeature importance:")
print(importance)


# Save feature importance
importance.to_csv(
    IMPORTANCE_PATH,
    index=False
)


# Sort and save reranked results
test_df = test_df.sort_values(
    ["query", "rerank_score"],
    ascending=[True, False]
)

test_df.to_csv(
    RESULTS_PATH,
    index=False
)


# Save trained model
joblib.dump(
    model,
    MODEL_PATH
)


print("\n----------------------------------------")
print("LightGBM reranking process completed.")
print("----------------------------------------")

print("\nModel saved at:")
print(MODEL_PATH)

print("\nReranked results saved at:")
print(RESULTS_PATH)

print("\nFeature importance saved at:")
print(IMPORTANCE_PATH)