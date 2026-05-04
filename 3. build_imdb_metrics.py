# build_imdb_metrics.py

# PURPOSE:
# Measure production supply vs demand using IMDb data and estimate financial opportunity

# INPUT:
# - title.basics.tsv.gz
# - title.ratings.tsv.gz
# - theme_priority_scores.csv

# OUTPUT:
# - imdb_theme_metrics.csv


import pandas as pd
import numpy as np
from pathlib import Path

# FILE PATHS
BASICS_FILE = Path("Data/imdb/title.basics.tsv.gz")
RATINGS_FILE = Path("Data/imdb/title.ratings.tsv.gz")
THEME_FILE = Path("Data/theme_priority_scores.csv")

OUTPUT_FILE = Path("Data/imdb_theme_metrics.csv")


# LOAD DATA
print("Loading IMDb datasets...")

basics = pd.read_csv(BASICS_FILE, sep="\t", low_memory=False)
ratings = pd.read_csv(RATINGS_FILE, sep="\t")

themes_df = pd.read_csv(THEME_FILE)


# CLEAN BASICS
print("Cleaning data...")

# Keep only movies & TV series
basics = basics[
    basics["titleType"].isin(["movie", "tvSeries"])
]

# Remove missing years
basics = basics[basics["startYear"] != "\\N"]
basics["startYear"] = basics["startYear"].astype(int)

# Keep relevant columns
basics = basics[[
    "tconst",
    "primaryTitle",
    "startYear",
    "genres"
]]


# MERGE RATINGS
df = basics.merge(ratings, on="tconst", how="inner")

# Remove missing genres
df = df[df["genres"] != "\\N"]


# FILTER RECENT CONTENT
df = df[df["startYear"] >= 2015]


# MAP THEMES → IMDb GENRES
# NOTE:
# IMDb genres are like: Action, Drama, Horror, Sci-Fi, etc.

theme_mapping = {
    "fantasy books": ["Fantasy"],
    "science fiction books": ["Sci-Fi"],
    "dystopian books": ["Sci-Fi"],
    "historical fiction books": ["History", "Drama"],
    "horror books": ["Horror"]
}


# CALCULATE METRICS
results = []

for theme, genres in theme_mapping.items():

    subset = df[df["genres"].str.contains("|".join(genres), na=False)]

    if len(subset) == 0:
        continue

    avg_rating = subset["averageRating"].mean()
    avg_votes = subset["numVotes"].mean()
    total_titles = len(subset)

    results.append({
        "theme": theme,
        "avg_rating": avg_rating,
        "avg_votes": avg_votes,
        "total_titles": total_titles
    })

metrics_df = pd.DataFrame(results)


# NORMALIZE
def normalize(series):
    return (series - series.min()) / (series.max() - series.min())

metrics_df["rating_score"] = normalize(metrics_df["avg_rating"])
metrics_df["popularity_score"] = normalize(metrics_df["avg_votes"])
metrics_df["supply_score"] = normalize(metrics_df["total_titles"])


# OPPORTUNITY LOGIC
# High demand + low supply = opportunity

merged = themes_df.merge(metrics_df, on="theme", how="left")

# Fill missing
merged = merged.fillna(0)

merged["opportunity_score"] = (
    0.5 * merged["priority_score"] +
    0.3 * (1 - merged["supply_score"]) +   # LOW supply = GOOD
    0.2 * merged["popularity_score"]
)


# ESTIMATE $$$
merged["estimated_value_millions"] = merged["opportunity_score"] * 50


# SORT
merged = merged.sort_values(
    by="opportunity_score",
    ascending=False
)


# SAVE
merged.to_csv(OUTPUT_FILE, index=False)

print("\n=== FINAL OPPORTUNITY ANALYSIS ===")
print(merged[[
    "theme",
    "priority_score",
    "total_titles",
    "opportunity_score",
    "estimated_value_millions"
]].head())

print(f"\nSaved to: {OUTPUT_FILE}")