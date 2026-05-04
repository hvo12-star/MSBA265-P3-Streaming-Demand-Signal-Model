# Streaming Demand Signal Model (P3)

## 1. Project Overview

This project builds a data-driven decision-support system to identify high-opportunity narrative themes and recommend specific book titles for potential streaming adaptation.

The goal is to answer two key business questions:
- Which themes show strong audience demand?
- Which titles within those themes should be adapted?

This is a rule-based analytical model combining:
- Google Trends (demand)
- IMDb (production supply)
- Google Books / curated datasets (titles)

---

## 2. Business Motivation

Streaming platforms often respond too late to emerging trends. There is a delay between demand growth and production response.

This delay can create missed engagement and revenue opportunities because platforms may enter a market after audience interest has already peaked or after competitors have already responded.

This project identifies those opportunity gaps early by comparing audience demand signals with existing production activity.

---

## 3. Pipeline Overview

Google Trends → Demand Modeling → IMDb Supply → Opportunity Model → Title Retrieval → Title Scoring → Final Recommendations

---

## 4. Folder Structure

P3/
│
├── Data/
│   ├── imdb/
│   │   ├── title.basics.tsv.gz
│   │   └── title.ratings.tsv.gz
│   │
│   ├── trends_theme_timeseries.csv
│   ├── clean_theme_candidates.csv
│   ├── eda_before_cleaning.png
│   ├── eda_after_feature_engineering.png
│   ├── theme_priority_scores.csv
│   ├── imdb_theme_metrics.csv
│   ├── fallback_titles.csv
│   └── title_recommendations.csv
│
├── build_themes.py
├── build_model.py
├── build_imdb_metrics.py
├── get_titles.py
├── requirements.txt
└── README.md

---

## 5. Setup Instructions

### Mac
cd /your/path/P3  
conda activate msba265  
pip install -r requirements.txt  

### Windows
cd C:\your\path\P3  
conda activate msba265  
pip install -r requirements.txt  

---

## 6. How to Run

Run in order:

python build_themes.py  
python build_model.py  
python build_imdb_metrics.py  
python get_titles.py  

---

## 7. Data Sources

### Google Trends
- Source: https://trends.google.com  
- Method: Manual CSV download  
- File: trends_theme_timeseries.csv  
- Keywords used:
  - "fantasy books"
  - "science fiction books"
  - "dystopian books"
  - "historical fiction books"
  - "horror books"

- Settings:
  - Region: United States
  - Time range: Past 12 months
  - Category: Books & Literature (if selected)
  - Data frequency: Weekly

- Description:
  This dataset contains weekly search interest values (0–100 scale) for each theme.  
  These values are normalized by Google Trends, meaning they represent relative popularity over time rather than absolute search volume.

- Why this matters:
  These keywords act as **proxies for audience demand**.  
  The model uses these signals to detect:
  - Which themes are popular
  - Which themes are growing
  - Which themes are accelerating

---

### IMDb Dataset
- Source: https://datasets.imdbws.com  
- Method: Manual download (no API required)
- Files used:
  - title.basics.tsv.gz  
  - title.ratings.tsv.gz  
- How to download:
  1. Go to: https://datasets.imdbws.com  

  2. Download:
     - title.basics.tsv.gz  
     - title.ratings.tsv.gz  

  3. Place both files into:
     Data/imdb/
- Key fields used:
  - titleType (movie, tvSeries)
  - primaryTitle
  - startYear
  - genres
  - averageRating
  - numVotes
- Data filtering:
  - Keep only:
    - Movies
    - TV series
  - Filter by theme keywords:
    - fantasy
    - science fiction
    - dystopian
    - historical
    - horror
- Description:
  This dataset represents existing content already produced in the market.
- Why this matters:
  IMDb data is used as a **proxy for production activity (supply)**.  
  If many titles already exist for a theme → high supply  
  If few titles exist → low supply  
  The model compares:
  - Demand (Google Trends)
  vs.
  - Supply (IMDb)
  This comparison enables **gap analysis** to identify under-served themes.

---

### Google Books API
- Source: https://developers.google.com/books/docs/v1/using  
- Purpose:
  Used to retrieve book titles related to the highest-priority theme.
- How it works:
  - The model selects the top theme (e.g., "fantasy books")
  - The script queries the Google Books API using that theme
  - Returns:
    - title
    - author
    - publication year
    - ratings (if available)
- Limitation:
  - Subject to rate limits (HTTP 429 errors)
  - May fail if too many requests are sent in a short time
- Important note:
  This API is used for **title-level recommendations**, not for model training.

---

### Fallback Dataset (CRITICAL)
- File: fallback_titles.csv  
- Location: Data/fallback_titles.csv  
- Why this exists:
  The Google Books API may fail due to rate limits.  
  To ensure the project is fully reproducible, a fallback dataset is provided. 
- How this dataset was created:
  Titles were manually collected from publicly available sources:
  - Google Books search results
  - Goodreads popular lists
  - Amazon bestseller rankings 
- Selection criteria:
  - Must match selected themes (e.g., fantasy books)
  - Must show signs of demand or popularity, such as:
    - High ratings
    - Strong fanbase
    - Recent trending activity
    - Existing adaptations
- Example titles:
  - Fourth Wing
  - Iron Flame
  - The Name of the Wind
  - Shadow and Bone
  - The Poppy War
- How it is used:
  If the API fails:
  → The script automatically loads this dataset  
  → Applies the same scoring logic  
  → Generates recommendations  
- Why this matters:
  This ensures:
  - The pipeline always runs successfully
  - Results can be reproduced without API dependency
  - The project reflects real-world constraints (imperfect data access)

---

## 8. EDA

### Before
- Raw 0–100 Google Trends scale
- Not interpretable directly

### After
Features created:
- avg_demand
- recent_demand
- slope
- acceleration
- volatility

---

## 9. Model Logic

Priority Score =  
0.30 × avg_demand  
+ 0.25 × recent_demand  
+ 0.25 × slope  
+ 0.15 × acceleration  
+ 0.05 × stability  

---

## 10. Opportunity Model

Demand (Google Trends)  
vs  
Supply (IMDb)

Core idea:

**High Demand + Low Production = Opportunity**

---

## 11. Title Recommendation System
The script get_titles.py works as follows:

### Step 1: Try API
- Uses Google Books API to fetch titles

### Step 2: Fallback (automatic)
If API fails:
- Switches to fallback_titles.csv
- No manual intervention needed

### Step 3: Scoring
Titles are ranked using:
- Theme priority score
- Public popularity signals
- Optional rating data (if API used)

Output:
title_recommendations.csv  

---

## 12. Key Results

Top Theme:
Fantasy Books

Reason:
- Highest demand
- Strong growth
- High acceleration

---

## 13. Business Insight

Themes with rising demand and lower production activity represent high-value opportunities because audience interest may not yet be fully captured by existing content.

The model does not estimate exact revenue. Instead, it ranks relative opportunity based on demand signals, supply proxies, and title-level recommendation potential.

---

## 14. Limitations

- Google Trends is normalized
- IMDb is indirect proxy
- API rate limits require fallback
- Financial estimates are approximate

---

## 15. Final Note

This project demonstrates how demand signals can be transformed into actionable content strategy insights, helping platforms act earlier and more effectively.
