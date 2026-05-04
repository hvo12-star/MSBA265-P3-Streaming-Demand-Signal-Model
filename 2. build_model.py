# build_model.py

# PURPOSE:
# This script builds the theme-level demand signal model for P3.

# It uses Google Trends time-series data to rank narrative themes based on audience demand signals.

# INPUT:
# Data/trends_theme_timeseries.csv

# OUTPUTS:
# Data/theme_priority_scores.csv
# Data/eda_before_cleaning.png
# Data/eda_after_feature_engineering.png

# HOW TO REPRODUCE:
# 1. Go to Google Trends.
# 2. Compare selected theme search terms together.
#    Example:
#    - fantasy books
#    - science fiction books
#    - dystopian books
#    - historical fiction books
#    - horror books
# 3. Set:
#    - Location: United States
#    - Time range: Past year
#    - Search type: Web Search
# 4. Download the "Interest over time" CSV.
# 5. Rename the downloaded file:
#    trends_theme_timeseries.csv
# 6. Place it inside the Data folder.
# 7. Run:
#    python build_model.py

# MODEL TYPE:
# This is a rule-based scoring model, not a trained machine
# learning model. It does not use train/test split.


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# 1. FILE PATHS
INPUT_FILE = Path("Data/trends_theme_timeseries.csv")
OUTPUT_FILE = Path("Data/theme_priority_scores.csv")
EDA_BEFORE_CHART = Path("Data/eda_before_cleaning.png")
EDA_AFTER_CHART = Path("Data/eda_after_feature_engineering.png")


# 2. LOAD GOOGLE TRENDS DATA
if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Missing file: {INPUT_FILE}\n"
        "Make sure the Google Trends interest-over-time CSV is named "
        "trends_theme_timeseries.csv and saved inside the Data folder."
    )

df = pd.read_csv(INPUT_FILE)


# 3. EDA BEFORE CLEANING / FEATURE ENGINEERING
# This section shows what the raw Google Trends dataset looks like before cleaning and before model features are created.

# This is useful for the report because it shows:
# - how many rows and columns exist
# - what the raw columns are
# - what the original data looks like
# - basic summary statistics

print("\n=== EDA BEFORE CLEANING / FEATURE ENGINEERING ===\n")

print("Raw dataset shape:")
print(df.shape)

print("\nRaw columns:")
print(df.columns.tolist())

print("\nRaw sample data:")
print(df.head())

print("\nRaw summary statistics:")
print(df.describe(include="all"))


# 4. CLEAN COLUMN NAMES
df.columns = [col.strip() for col in df.columns]


# 5. VALIDATE AND CLEAN TIME COLUMN
if "Time" not in df.columns:
    raise ValueError(
        "The dataset must contain a column named 'Time'. "
        "Check the Google Trends CSV export."
    )

df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df = df.dropna(subset=["Time"])


# 6. IDENTIFY THEME COLUMNS
theme_columns = [col for col in df.columns if col != "Time"]

if len(theme_columns) == 0:
    raise ValueError(
        "No theme columns found. The dataset should include one column "
        "per theme after the Time column."
    )


# 7. CONVERT THEME VALUES TO NUMERIC
for col in theme_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=theme_columns, how="all")


# 8. SAVE EDA BEFORE CHART
# This chart shows the raw Google Trends time-series lines. Use this in the report as the "before feature engineering" EDA visual.
plt.figure(figsize=(10, 6))

for theme in theme_columns:
    plt.plot(df["Time"], df[theme], label=theme)

plt.title("EDA Before Feature Engineering: Raw Google Trends Time Series")
plt.xlabel("Time")
plt.ylabel("Google Trends Search Interest")
plt.legend()
plt.tight_layout()
plt.savefig(EDA_BEFORE_CHART)
plt.close()

print(f"\nEDA before chart saved to: {EDA_BEFORE_CHART}")


# 9. BUILD DEMAND METRICS
# For each theme, we calculate:
# 1. Average Demand:
#    Average Google Trends interest score over the past year.
# 2. Recent Demand:
#    Average Google Trends interest score over the most recent 4 weeks.
# 3. Slope:
#    Linear trend slope over the full time period.
#    Positive slope = upward trend.
# 4. Acceleration:
#    Difference between the second-half average and first-half average.
#    Positive acceleration = recent demand is stronger than earlier demand.
# 5. Volatility:
#    Standard deviation of search interest values.
#    Lower volatility = more stable demand signal.

results = []

for theme in theme_columns:
    series = df[theme].dropna()

    if len(series) < 4:
        print(f"Skipping {theme}: not enough data points.")
        continue

    avg_demand = series.mean()
    recent_demand = series.tail(4).mean()

    x = np.arange(len(series))
    slope = np.polyfit(x, series.values, 1)[0]

    midpoint = len(series) // 2
    first_half_avg = series.iloc[:midpoint].mean()
    second_half_avg = series.iloc[midpoint:].mean()
    acceleration = second_half_avg - first_half_avg

    volatility = series.std()

    results.append({
        "theme": theme,
        "avg_demand_raw": avg_demand,
        "recent_demand_raw": recent_demand,
        "slope_raw": slope,
        "acceleration_raw": acceleration,
        "volatility_raw": volatility
    })

results_df = pd.DataFrame(results)

if results_df.empty:
    raise ValueError("No theme metrics were calculated. Check your input data.")


# 10. EDA AFTER FEATURE ENGINEERING
# This section shows what the data looks like after turning the raw time-series values into model-ready features.
print("\n=== EDA AFTER FEATURE ENGINEERING ===\n")

print("Feature dataset:")
print(results_df)

print("\nFeature summary statistics:")
print(results_df.describe(include="all"))


# 11. NORMALIZATION FUNCTION
def normalize_series(series):
    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        return pd.Series([0.0] * len(series), index=series.index)

    return (series - min_val) / (max_val - min_val)


# 12. NORMALIZE METRICS
# Higher is better:
# - average demand
# - recent demand
# - slope
# - acceleration

# Lower is better:
# - volatility

# So volatility is inverted and renamed stability_score.

results_df["avg_demand_score"] = normalize_series(results_df["avg_demand_raw"])
results_df["recent_demand_score"] = normalize_series(results_df["recent_demand_raw"])
results_df["slope_score"] = normalize_series(results_df["slope_raw"])
results_df["acceleration_score"] = normalize_series(results_df["acceleration_raw"])

volatility_normalized = normalize_series(results_df["volatility_raw"])
results_df["stability_score"] = 1 - volatility_normalized


# 13. PRIORITY SCORE

# Formula:
# Priority Score =
# 30% average demand
# + 25% recent demand
# + 25% slope
# + 15% acceleration
# + 5% stability

results_df["priority_score"] = (
    0.30 * results_df["avg_demand_score"] +
    0.25 * results_df["recent_demand_score"] +
    0.25 * results_df["slope_score"] +
    0.15 * results_df["acceleration_score"] +
    0.05 * results_df["stability_score"]
)


# 14. SORT RESULTS
results_df = results_df.sort_values(
    by="priority_score",
    ascending=False
).reset_index(drop=True)


# 15. SAVE AFTER FEATURE ENGINEERING CHART
# This chart shows the final priority scores by theme. Use this in the report as the "after feature engineering/model output" visual.

plt.figure(figsize=(10, 6))
plt.bar(results_df["theme"], results_df["priority_score"])
plt.title("EDA After Feature Engineering: Theme Priority Scores")
plt.xlabel("Theme")
plt.ylabel("Priority Score")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(EDA_AFTER_CHART)
plt.close()

print(f"\nEDA after chart saved to: {EDA_AFTER_CHART}")


# 16. SAVE RESULTS
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
results_df.to_csv(OUTPUT_FILE, index=False)


# 17. PRINT FINAL RESULTS
print("\n=== THEME PRIORITY RANKING ===\n")

print(results_df[[
    "theme",
    "avg_demand_raw",
    "recent_demand_raw",
    "slope_raw",
    "acceleration_raw",
    "volatility_raw",
    "priority_score"
]])

print("\nSaved to:", OUTPUT_FILE)


# 18. BEGINNER-FRIENDLY INTERPRETATION
top_theme = results_df.iloc[0]

print("\n=== INTERPRETATION ===\n")
print(
    f"The highest-ranked theme is '{top_theme['theme']}'. "
    "This means it performed strongest overall based on demand level, "
    "recent demand, growth trend, acceleration, and stability."
)

print(
    "\nThis model should be interpreted as a decision-support ranking model. "
    "It does not prove that a theme will become a successful show or movie. "
    "Instead, it identifies which themes may deserve closer review based on "
    "public search-interest signals."
)