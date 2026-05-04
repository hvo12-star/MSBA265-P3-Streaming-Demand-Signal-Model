# get_titles.py

# PURPOSE:
# This script creates title-level recommendations for the highest-ranked theme from the demand model.

# The preferred method is to use the Google Books API. However, the Google Books API may fail because of rate limits such as HTTP 429 "Too Many Requests."

# To keep the project reproducible, this script includes a fallback method. If the API fails, it loads a curated public title dataset from:
# Data/fallback_titles.csv

# The fallback dataset is NOT made up. It should be curated from publicly available sources such as:
# - Google Books search results
# - Goodreads popular lists
# - Amazon bestseller rankings
# - publicly visible reader/rating/trending signals

# INPUTS:
# Data/theme_priority_scores.csv
# Data/fallback_titles.csv

# OUTPUT:
# Data/title_recommendations.csv

# HOW TO REPRODUCE:
# 1. Run build_model.py first.
#    This creates Data/theme_priority_scores.csv.
# 2. Make sure fallback_titles.csv exists in the Data folder.
#    Required columns:
#    title, author, source, notes
# 3. Run:
#    python get_titles.py
# 4. The script will:
#    - identify the top-ranked theme
#    - try Google Books API
#    - switch to fallback data if API fails
#    - clean and score titles
#    - save Data/title_recommendations.csv


import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path


# 1. FILE PATHS
THEME_SCORE_FILE = Path("Data/theme_priority_scores.csv")
FALLBACK_FILE = Path("Data/fallback_titles.csv")
OUTPUT_FILE = Path("Data/title_recommendations.csv")


# 2. SETTINGS
# USE_API controls whether the script tries Google Books API.

# True  = try API first, then fallback if API fails
# False = skip API and use fallback dataset only

# For this project, keep True to demonstrate the semi-automated pipeline, but the fallback protects reproducibility.

USE_API = True

MAX_RESULTS = 20
RETRIES = 3
WAIT_SECONDS = 10


# 3. LOAD TOP THEME
if not THEME_SCORE_FILE.exists():
    raise FileNotFoundError(
        "Missing Data/theme_priority_scores.csv. "
        "Run build_model.py before running get_titles.py."
    )

theme_df = pd.read_csv(THEME_SCORE_FILE)

if theme_df.empty:
    raise ValueError("theme_priority_scores.csv is empty.")

top_theme = theme_df.iloc[0]["theme"]
top_theme_score = theme_df.iloc[0]["priority_score"]

print("\nTop theme selected from model:")
print(top_theme)
print("Theme priority score:", top_theme_score)


# 4. GOOGLE BOOKS API SEARCH
# This function searches Google Books for books related to the top-ranked theme.

# Example: top_theme = "fantasy books"

# The API can return:
# - title
# - authors
# - published date
# - description
# - categories
# - average rating
# - ratings count
# - page count

# If Google returns HTTP 429, the script retries with a delay.
# If it still fails, the script falls back to fallback_titles.csv.
def search_google_books(query, max_results=20, retries=3, wait_seconds=10):
    url = "https://www.googleapis.com/books/v1/volumes"

    params = {
        "q": query,
        "maxResults": max_results,
        "printType": "books",
        "langRestrict": "en",
        "orderBy": "relevance"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for attempt in range(retries):
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=20
        )

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])

            rows = []

            for item in items:
                volume = item.get("volumeInfo", {})

                rows.append({
                    "title": volume.get("title", ""),
                    "author": ", ".join(volume.get("authors", [])),
                    "source": "Google Books API",
                    "notes": "API result",
                    "published_date": volume.get("publishedDate", ""),
                    "description": volume.get("description", ""),
                    "categories": ", ".join(volume.get("categories", [])),
                    "average_rating": volume.get("averageRating", np.nan),
                    "ratings_count": volume.get("ratingsCount", 0),
                    "page_count": volume.get("pageCount", np.nan),
                    "source_theme": query,
                    "collection_method": "api"
                })

            return pd.DataFrame(rows)

        elif response.status_code == 429:
            print(
                f"Rate limited by Google Books API. "
                f"Retrying {attempt + 1}/{retries}..."
            )
            time.sleep(wait_seconds)

        else:
            raise RuntimeError(
                f"Google Books API request failed. "
                f"Status code: {response.status_code}"
            )

    raise RuntimeError(
        "Google Books API request failed after multiple retries "
        "because of rate limits."
    )


# 5. LOAD FALLBACK TITLE DATA
# This function loads a curated public title dataset.

# Required columns: title, author, source, notes

# Example row: Fourth Wing, Rebecca Yarros, Goodreads, High popularity

# The fallback dataset exists so the project can still run even when the API is blocked or rate-limited.
def load_fallback_titles():
    if not FALLBACK_FILE.exists():
        raise FileNotFoundError(
            "Missing Data/fallback_titles.csv. "
            "Create this file using publicly available title sources "
            "such as Goodreads, Amazon, or Google Books search results."
        )

    fallback_df = pd.read_csv(FALLBACK_FILE)

    required_cols = ["title", "author", "source", "notes"]

    for col in required_cols:
        if col not in fallback_df.columns:
            raise ValueError(
                f"Missing required column: {col}. "
                "fallback_titles.csv must include: "
                "title, author, source, notes."
            )

    fallback_df["published_date"] = ""
    fallback_df["description"] = ""
    fallback_df["categories"] = top_theme
    fallback_df["average_rating"] = np.nan
    fallback_df["ratings_count"] = 0
    fallback_df["page_count"] = np.nan
    fallback_df["source_theme"] = top_theme
    fallback_df["collection_method"] = "fallback_curated_public_sources"

    return fallback_df


# 6. CLEAN TITLE DATA
# This function cleans either API data or fallback data.
def clean_titles(title_df):
    if title_df.empty:
        return title_df

    df = title_df.copy()

    df["title"] = df["title"].astype(str).str.strip()
    df["author"] = df["author"].astype(str).str.strip()
    df["source"] = df["source"].astype(str).str.strip()
    df["notes"] = df["notes"].astype(str).str.strip()

    df = df[df["title"] != ""]
    df = df.drop_duplicates(subset=["title", "author"])

    df["ratings_count"] = pd.to_numeric(
        df["ratings_count"],
        errors="coerce"
    ).fillna(0)

    df["average_rating"] = pd.to_numeric(
        df["average_rating"],
        errors="coerce"
    )

    df["page_count"] = pd.to_numeric(
        df["page_count"],
        errors="coerce"
    )

    df["published_year"] = (
        df["published_date"]
        .astype(str)
        .str.extract(r"(\d{4})")
    )

    df["published_year"] = pd.to_numeric(
        df["published_year"],
        errors="coerce"
    )

    return df


# 7. NORMALIZATION FUNCTION
# Converts numeric values into a 0–1 scale. This helps combine metrics that are measured differently.
def normalize_series(series):
    series = pd.to_numeric(series, errors="coerce").fillna(0)

    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        return pd.Series([0.0] * len(series), index=series.index)

    return (series - min_val) / (max_val - min_val)


# 8. SCORE TITLES
# API results and fallback results are scored slightly differently because fallback data does not always have ratings_count or average_rating.
# The goal is not to prove success. The goal is to rank candidate titles for further business review.
def score_titles(title_df, theme_score):
    if title_df.empty:
        return title_df

    df = title_df.copy()

    df["theme_priority_score"] = theme_score

    # API-based numeric signals
    df["ratings_count_log"] = np.log1p(
        pd.to_numeric(df["ratings_count"], errors="coerce").fillna(0)
    )

    df["ratings_count_score"] = normalize_series(df["ratings_count_log"])
    df["average_rating_score"] = normalize_series(df["average_rating"])
    df["publication_recency_score"] = normalize_series(df["published_year"])

    # Fallback note-based signals
    df["public_signal_score"] = 0

    df["public_signal_score"] += df["notes"].str.contains(
        "high", case=False, na=False
    ).astype(int) * 2

    df["public_signal_score"] += df["notes"].str.contains(
        "trending", case=False, na=False
    ).astype(int) * 2

    df["public_signal_score"] += df["notes"].str.contains(
        "viral", case=False, na=False
    ).astype(int) * 1

    df["public_signal_score"] += df["notes"].str.contains(
        "proven", case=False, na=False
    ).astype(int) * 1

    df["public_signal_score"] += df["notes"].str.contains(
        "fanbase", case=False, na=False
    ).astype(int) * 1

    df["public_signal_score"] += df["notes"].str.contains(
        "requested", case=False, na=False
    ).astype(int) * 2

    df["public_signal_score"] += df["notes"].str.contains(
        "adapted", case=False, na=False
    ).astype(int) * 1

    df["public_signal_score_norm"] = normalize_series(
        df["public_signal_score"]
    )

    # Final title score:
    # - theme score keeps the title connected to the top model theme
    # - public signals help fallback rows rank properly
    # - API numeric fields help if API data is available
    df["title_opportunity_score"] = (
        0.40 * df["theme_priority_score"] +
        0.25 * df["public_signal_score_norm"] +
        0.15 * df["ratings_count_score"] +
        0.10 * df["average_rating_score"] +
        0.10 * df["publication_recency_score"]
    )

    df = df.sort_values(
        by="title_opportunity_score",
        ascending=False
    ).reset_index(drop=True)

    return df


# 9. MAIN PROGRAM
def main():
    used_fallback = False

    if USE_API:
        try:
            print("\nSearching Google Books API...")
            raw_titles = search_google_books(
                top_theme,
                max_results=MAX_RESULTS,
                retries=RETRIES,
                wait_seconds=WAIT_SECONDS
            )

            print("Titles returned from API:", len(raw_titles))

            if raw_titles.empty:
                print("API returned no titles. Switching to fallback dataset.")
                raw_titles = load_fallback_titles()
                used_fallback = True

        except Exception as error:
            print("\nGoogle Books API failed.")
            print("Reason:", error)
            print("\nSwitching to fallback title dataset...")
            raw_titles = load_fallback_titles()
            used_fallback = True

    else:
        print("\nUSE_API is False. Loading fallback title dataset...")
        raw_titles = load_fallback_titles()
        used_fallback = True

    print("\nCleaning title data...")
    clean_df = clean_titles(raw_titles)

    print("Titles after cleaning:", len(clean_df))

    if clean_df.empty:
        raise ValueError(
            "No valid title records were available after cleaning."
        )

    print("\nScoring title recommendations...")
    scored_df = score_titles(clean_df, top_theme_score)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    scored_df.to_csv(OUTPUT_FILE, index=False)

    print("\n=== TITLE RECOMMENDATIONS ===\n")

    display_cols = [
        "title",
        "author",
        "source",
        "notes",
        "collection_method",
        "title_opportunity_score"
    ]

    print(scored_df[display_cols].head(10))

    print("\nSaved to:", OUTPUT_FILE)

    print("\n=== INTERPRETATION ===\n")

    print(
        f"The model selected '{top_theme}' as the highest-opportunity "
        "theme. This script then generated title-level recommendations "
        "for that theme."
    )

    if used_fallback:
        print(
            "\nBecause the Google Books API was unavailable or rate-limited, "
            "the script used the fallback title dataset. This fallback dataset "
            "was curated from publicly available sources such as Google Books "
            "search results, Goodreads lists, and Amazon bestseller rankings."
        )
    else:
        print(
            "\nThe title recommendations were generated using live Google "
            "Books API results."
        )

    print(
        "\nImportant limitation: These titles are candidate recommendations, "
        "not final production decisions. A streaming platform would still need "
        "to evaluate rights availability, production cost, target audience fit, "
        "and competitive activity before adapting a title."
    )


if __name__ == "__main__":
    main()