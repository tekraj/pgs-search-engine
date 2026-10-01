import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import ndcg_score


# Load data
DATA_PATH = r"C:\Users\Acer\Desktop\search\pgs-search-engine\search-engine\test\ranking_traning_data.csv"

df = pd.read_csv(DATA_PATH)

print("Dataset shape:", df.shape)


# Features used for ranking
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


# Clean missing values
df[FEATURES] = df[FEATURES].fillna(0)
df[TARGET] = df[TARGET].fillna(0)


# Split data by query
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


# Keep documents of the same query together
train_df = train_df.sort_values("query")
test_df = test_df.sort_values("query")


# Training data
X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]


# Number of documents for each query
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
    n_estimators=200,
    num_leaves=31,
    random_state=42,
    verbosity=-1
)


# Train model
print("\nTraining LightGBM...")

model.fit(
    X_train,
    y_train,
    group=train_groups,
    eval_set=[(X_test, y_test)],
    eval_group=[test_groups]
)

print("Training completed.")


# Predict ranking scores
test_df["rerank_score"] = model.predict(
    X_test
)


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


if scores:
    average_ndcg = np.mean(scores)

    print(
        f"\nNDCG@5: {average_ndcg:.4f}"
    )


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


importance.to_csv(
    "feature_importance.csv",
    index=False
)


# Save reranked results
test_df = test_df.sort_values(
    ["query", "rerank_score"],
    ascending=[True, False]
)

test_df.to_csv(
    "reranked_results.csv",
    index=False
)


# Save model
joblib.dump(
    model,
    "lightgbm_reranker.pkl"
)

print("\nModel saved as:")
print("lightgbm_reranker.pkl")

print("\nReranked results saved as:")
print("reranked_results.csv")

print("\nFeature importance saved as:")
print("feature_importance.csv")