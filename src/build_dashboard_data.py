"""Aggregate the cleaned data into docs/data.json for the interactive dashboard (GitHub Pages)."""
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "listings_clean.csv"
GEO = ROOT / "data" / "raw" / "neighbourhoods.geojson"
REPORTS = ROOT / "reports"
OUT = ROOT / "docs" / "data.json"
MAP_W, MAP_H, MIN_LISTINGS = 640, 520, 5


def r(x, n=0):
    return None if pd.isna(x) else (int(round(x)) if n == 0 else round(float(x), n))


def simplify(points, tol):
    """Drop points closer than `tol` to the previously kept point (cheap simplification)."""
    kept = [points[0]]
    for p in points[1:]:
        if math.hypot(p[0] - kept[-1][0], p[1] - kept[-1][1]) >= tol:
            kept.append(p)
    return kept if len(kept) >= 3 else points


def build_map(df):
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    lons = [c[0] for f in geo["features"] for poly in f["geometry"]["coordinates"] for ring in poly for c in ring]
    lats = [c[1] for f in geo["features"] for poly in f["geometry"]["coordinates"] for ring in poly for c in ring]
    lat0 = math.radians((min(lats) + max(lats)) / 2)
    xs = [lon * math.cos(lat0) for lon in lons]
    minx, maxx, miny, maxy = min(xs), max(xs), min(lats), max(lats)
    scale = min(MAP_W / (maxx - minx), MAP_H / (maxy - miny))

    def proj(lon, lat):
        return ((lon * math.cos(lat0) - minx) * scale, (maxy - lat) * scale)

    stats = df.groupby("neighbourhood").agg(listings=("id", "size"), median_price=("price", "median"))
    shapes = []
    for f in geo["features"]:
        name = f["properties"]["neighbourhood"]
        d = []
        for poly in f["geometry"]["coordinates"]:
            for ring in poly:
                pts = simplify([proj(*c) for c in ring], 1.2)
                d.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
        s = stats.loc[name] if name in stats.index else None
        listings = int(s["listings"]) if s is not None else 0
        shapes.append({
            "name": name, "district": f["properties"]["neighbourhood_group"], "path": "".join(d),
            "listings": listings,
            "median_price": r(s["median_price"]) if s is not None and listings >= MIN_LISTINGS else None,
        })
    return {"width": round((maxx - minx) * scale), "height": round((maxy - miny) * scale), "shapes": shapes}


def main():
    df = pd.read_csv(DATA)
    short = df[df["short_term"]]

    districts = (df.groupby("district").agg(
        listings=("id", "size"), median_price=("price", "median"), avg_price=("price", "mean"),
        pct_entire=("room_type", lambda s: 100 * (s == "Entire home/apt").mean()),
        avg_rating=("review_score", "mean"), avg_booked_nights=("est_occupancy_nights", "mean"),
    ).reset_index().sort_values("median_price", ascending=False))

    lic_order = ["Registration number", "Business / host disclosure", "Exempt", "Other", "Missing"]
    licence = {}
    for label, part in [("Short-term (< 30 nights)", short), ("Mid/long-term (30+ nights)", df[~df["short_term"]])]:
        shares = part["license_status"].value_counts(normalize=True)
        licence[label] = {k: r(100 * shares.get(k, 0), 1) for k in lic_order}

    bins = list(range(0, 520, 20))
    hist, _ = np.histogram(df["price"].clip(upper=499), bins=bins)

    top10_share = (df.groupby("host_id").size().sort_values(ascending=False).head(10).sum() / len(df)) * 100
    comparison = pd.read_csv(REPORTS / "model_comparison.csv")
    importance = pd.read_csv(REPORTS / "feature_importance.csv")

    data = {
        "snapshot": "19 September 2026",
        "kpis": {
            "listings": len(df),
            "median_price": r(df["price"].median()),
            "pct_entire": r(100 * (df["room_type"] == "Entire home/apt").mean(), 1),
            "pct_multi_host": r(100 * (df["host_type"] == "Multi-listing host").mean(), 1),
            "top10_host_share": r(top10_share, 1),
            "pct_short_term_missing_licence": r(100 * (short["license_status"] == "Missing").mean(), 1),
            "superhost_price_premium": r(100 * (df[df.superhost]["price"].median() / df[~df.superhost]["price"].median() - 1), 0),
        },
        "districts": [{k: (r(v, 1) if isinstance(v, float) else v) for k, v in row.items()} for row in districts.to_dict("records")],
        "room_types": [{"room_type": k, "listings": int(v["count"]), "median_price": r(v["median"])}
                       for k, v in df.groupby("room_type")["price"].agg(["count", "median"]).sort_values("count", ascending=False).iterrows()],
        "licence": licence,
        "price_hist": {"bins": bins, "counts": hist.tolist()},
        "model": {
            "comparison": comparison.to_dict("records"),
            "importance": [{"feature": f, "importance": r(i, 3)} for f, i in importance.values],
        },
        "map": build_map(df),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"saved {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)")
    print(json.dumps(data["kpis"], indent=1)); print(json.dumps(licence, indent=1))


if __name__ == "__main__":
    main()
