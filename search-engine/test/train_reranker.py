import os
import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import ndcg_score


# Path of the project files
BASE_DIR = r"C:\Users\Acer\Desktop\search\pgs-search-engine\search-engine\test"

DATA_PATH = os.path.join(BASE_DIR, "ranking_traning_data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "lightgbm_reranker.pkl")
IMPORTANCE_PATH = os.path.join(BASE_DIR, "feature_importance.csv")
RESULTS_PATH = os.path.join(BASE_DIR, "reranked_results.csv")


# Load the training data
df = pd.read_csv(DATA_PATH)

print("Dataset shape:", df.shape)


# Features that will be used by the ranking model
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


# Check if all required columns are present
required_columns = FEATURES + [TARGET, "query"]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"These columns are missing: {missing_columns}"
    )


# Replace missing values with 0
df[FEATURES] = df[FEATURES].fillna(0)
df[TARGET] = df[TARGET].fillna(0)


# Split the data based on queries
# This keeps documents from the same query in the same dataset
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


# Sort the data by query
train_df = train_df.sort_values("query")
test_df = test_df.sort_values("query")


print("Training rows:", len(train_df))
print("Testing rows:", len(test_df))


# Select features and target
X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]


# Find the number of documents for each query
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


# Create the LightGBM ranking model
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


# Predict scores for the test documents
test_df["rerank_score"] = model.predict(X_test)


# Calculate NDCG@5 for each query
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


# Calculate the average NDCG
if scores:
    average_ndcg = np.mean(scores)

    print(
        f"\nAverage NDCG@5: {average_ndcg:.4f}"
    )

    print(
        "Number of queries evaluated:",
        len(scores)
    )


# Check which features were important to the model
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


# Sort the results using the predicted ranking score
test_df = test_df.sort_values(
    ["query", "rerank_score"],
    ascending=[True, False]
)


# Save the reranked results
test_df.to_csv(
    RESULTS_PATH,
    index=False
)


# Save the trained model
joblib.dump(
    model,
    MODEL_PATH
)


print("\nModel saved as:")
print(MODEL_PATH)

print("\nReranked results saved as:")
print(RESULTS_PATH)

print("\nFeature importance saved as:")
print(IMPORTANCE_PATH)

print("\nLightGBM reranking process completed.")