# build_themes.py

# PURPOSE:
# Clean Google Trends "rising queries" CSV and generate a data-driven list of narrative themes for the demand model.

# WHY THIS MATTERS:
# This replaces manual theme selection with a reproducible, data-driven pipeline using Google Trends.

# INPUT:
# Data/searched_with_rising_queries.csv

# OUTPUT:
# 1. Data/clean_theme_candidates.csv
# 2. themes.py

# HOW TO REPRODUCE:
# 1. Go to Google Trends
# 2. Search: "book genres"
# 3. Set:
#    - Location: United States
#    - Time range: Past 12 months
#    - Search type: Web Search
# 4. Download "Related queries" CSV
# 5. Rename file:
#    searched_with_rising_queries.csv
# 6. Place inside Data folder
# 7. Run:
#    python build_themes.py


import re
import pandas as pd
from pathlib import Path

# 1. FILE PATHS
INPUT_FILE = Path("Data/searched_with_rising_queries.csv")
OUTPUT_CSV = Path("Data/clean_theme_candidates.csv")
OUTPUT_PY = Path("themes.py")

# 2. FILTER LISTS
# Remove irrelevant domains
IRRELEVANT_KEYWORDS = [
    "music",
    "movie",
    "film",
    "bedford",
    "goodreads",
    "good reads",
]

# Remove generic search phrases
GENERIC_KEYWORDS = [
    "book genres",
    "books genres",
    "book genre",
    "genre",
    "genres",
    "list",
    "what are",
    "types of",
    "all book",
    "book categories",
    "book topics",
    "book themes",
    "explained",
]

# Remove definition-style queries
INVALID_PATTERNS = [
    "definition",
    "meaning",
    "what is",
    "types of",
    "list",
]

# Remove overly broad themes
WEAK_THEMES = [
    "fiction books",
    "books",
]

# Keep only queries that look like narrative themes
VALID_THEME_KEYWORDS = [
    "fiction",
    "thriller",
    "romance",
    "fantasy",
    "dystopian",
    "science fiction",
    "historical",
    "classic",
    "children",
    "mystery",
    "horror",
    "crime",
    "literary",
]

# 3. HELPER FUNCTIONS
def clean_text(text):
    text = str(text).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_irrelevant(query):
    return any(word in query for word in IRRELEVANT_KEYWORDS)


def is_too_generic(query):
    return any(word == query or word in query for word in GENERIC_KEYWORDS)


def is_bad_theme(query):
    return any(word in query for word in INVALID_PATTERNS)


def is_weak_theme(query):
    return query in WEAK_THEMES


def is_valid_theme(query):
    return any(word in query for word in VALID_THEME_KEYWORDS)


def standardize_theme(query):
    """
    Convert raw queries into consistent search terms.
    """

    query = clean_text(query)

    replacements = {
        "science fiction": "science fiction books",
        "historical fiction": "historical fiction books",
        "realistic fiction": "realistic fiction books",
        "literary fiction": "literary fiction books",
        "classic books": "classic literature books",
        "children's books": "children books",
        "dystopian books": "dystopian books",
        "fantasy": "fantasy books",
        "romance genres": "romance novels",
        "horror": "horror books",
        "mystery": "mystery books",
    }

    if query in replacements:
        return replacements[query]

    if "books" in query or "novels" in query:
        return query

    if "fiction" in query:
        return f"{query} books"

    return f"{query} books"


# 4. LOAD DATA
if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Missing file: {INPUT_FILE}\n"
        "Download from Google Trends and place it in Data folder."
    )

df = pd.read_csv(INPUT_FILE)

df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

# 5. CLEAN TEXT
df["query_clean"] = df["query"].apply(clean_text)

# 6. FILTER PIPELINE
df = df[~df["query_clean"].apply(is_irrelevant)]
df = df[~df["query_clean"].apply(is_too_generic)]
df = df[~df["query_clean"].apply(is_bad_theme)]
df = df[df["query_clean"].apply(is_valid_theme)]
df = df[~df["query_clean"].apply(is_weak_theme)]

# 7. STANDARDIZE THEMES
df["theme_query"] = df["query_clean"].apply(standardize_theme)

# 8. CLEAN NUMERIC VALUES
df["increase_percent_clean"] = (
    df["increase_percent"]
    .astype(str)
    .str.replace("%", "", regex=False)
    .str.replace("+", "", regex=False)
)

df["increase_percent_clean"] = pd.to_numeric(
    df["increase_percent_clean"], errors="coerce"
)

df["search_interest"] = pd.to_numeric(
    df["search_interest"], errors="coerce"
)

# 9. RANK THEMES
df = df.sort_values(
    by=["increase_percent_clean", "search_interest"],
    ascending=False
)

df = df.drop_duplicates(subset=["theme_query"])

# 10. SAVE CLEAN DATA
df[[
    "query",
    "theme_query",
    "search_interest",
    "increase_percent",
    "increase_percent_clean"
]].to_csv(OUTPUT_CSV, index=False)

# 11. CREATE themes.py
themes = df["theme_query"].tolist()

with open(OUTPUT_PY, "w") as f:
    f.write("# themes.py\n")
    f.write("# Auto-generated from Google Trends data\n\n")
    f.write("THEMES = [\n")
    for theme in themes:
        f.write(f'    "{theme}",\n')
    f.write("]\n")

# 12. PRINT RESULTS
print("Cleaned theme candidates saved to:", OUTPUT_CSV)
print("themes.py created:", OUTPUT_PY)

print("\nNumber of final themes:", len(themes))
print("\nFinal themes:")
for theme in themes:
    print("-", theme)