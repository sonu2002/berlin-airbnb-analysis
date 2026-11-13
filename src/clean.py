"""Clean the raw Inside Airbnb listings file into an analysis-ready table."""
from pathlib import Path
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "listings.csv.gz"
OUT = ROOT / "data" / "processed" / "listings_clean.csv"

# Prices outside this range are almost always placeholder or error values
MIN_PRICE, MAX_PRICE = 15, 1000

DISTRICT_NAMES = {
    "Charlottenburg-Wilm.": "Charlottenburg-Wilmersdorf",
    "Tempelhof - Schöneberg": "Tempelhof-Schöneberg",
    "Treptow - Köpenick": "Treptow-Köpenick",
    "Steglitz - Zehlendorf": "Steglitz-Zehlendorf",
    "Marzahn - Hellersdorf": "Marzahn-Hellersdorf",
}

REGISTRATION_PATTERN = re.compile(r"\b\d{2}/Z/[A-Z]{2}/\d{5,6}-\d{2}\b", re.IGNORECASE)


def parse_price(series: pd.Series) -> pd.Series:
    """'$1,234.00' -> 1234.0 (Inside Airbnb uses '$' even for EUR listings)."""
    return pd.to_numeric(series.astype(str).str.replace(r"[^\d.]", "", regex=True), errors="coerce")


def classify_license(value) -> str:
    """Group the free-text licence field into four categories."""
    if pd.isna(value) or not str(value).strip():
        return "Missing"
    text = str(value)
    if REGISTRATION_PATTERN.search(text):
        return "Registration number"
    if "exempt" in text.lower():
        return "Exempt"
    if "legal entity" in text.lower() or "first name and last name" in text.lower() or "trade register" in text.lower():
        return "Business / host disclosure"
    return "Other"


def parse_bathrooms(text) -> float:
    """'1.5 baths' -> 1.5, 'Half-bath' -> 0.5, 'Shared half-bath' -> 0.5."""
    if pd.isna(text):
        return np.nan
    text = str(text).lower()
    if "half" in text:
        return 0.5
    match = re.search(r"(\d+(\.\d+)?)", text)
    return float(match.group(1)) if match else np.nan


def clean(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "id": df["id"],
        "district": df["neighbourhood_group_cleansed"].replace(DISTRICT_NAMES),
        "neighbourhood": df["neighbourhood_cleansed"],
        "latitude": df["latitude"],
        "longitude": df["longitude"],
        "room_type": df["room_type"],
        "property_type": df["property_type"],
        "accommodates": df["accommodates"],
        "bedrooms": df["bedrooms"],
        "beds": df["beds"],
        "bathrooms": df["bathrooms_text"].map(parse_bathrooms),
        "shared_bath": df["bathrooms_text"].astype(str).str.contains("shared", case=False),
        "price": parse_price(df["price"]),
        "minimum_nights": df["minimum_nights"],
        "availability_365": df["availability_365"],
        "number_of_reviews": df["number_of_reviews"],
        "reviews_ltm": df["number_of_reviews_ltm"],
        "review_score": df["review_scores_rating"],
        "superhost": df["host_is_superhost"].eq("t"),
        "host_id": df["host_id"],
        "host_listings": df["calculated_host_listings_count"],
        "est_occupancy_nights": df["estimated_occupancy_l365d"],
        "est_revenue": df["estimated_revenue_l365d"],
        "amenities_count": df["amenities"].fillna("[]").str.count('",') + 1,
        "license_status": df["license"].map(classify_license),
    })
    out = out[out["price"].between(MIN_PRICE, MAX_PRICE)].copy()
    out["price_per_guest"] = (out["price"] / out["accommodates"].clip(lower=1)).round(2)
    out["host_type"] = np.where(out["host_listings"] > 1, "Multi-listing host", "Single-listing host")
    out["short_term"] = out["minimum_nights"] < 30   # Berlin: < 30 nights counts as short-term letting
    return out.reset_index(drop=True)


def main() -> None:
    raw = pd.read_csv(RAW, low_memory=False)
    cleaned = clean(raw)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(OUT, index=False)
    print(f"raw listings: {len(raw):,}  →  priced & cleaned: {len(cleaned):,}")
    print(f"saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
