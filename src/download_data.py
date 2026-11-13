"""Download the Inside Airbnb snapshot for Berlin used in this project."""
from pathlib import Path
import urllib.request

SNAPSHOT = "2026-09-19"
BASE = f"https://data.insideairbnb.com/germany/be/berlin/{SNAPSHOT}"
FILES = {
    "listings.csv.gz": f"{BASE}/data/listings.csv.gz",
    "neighbourhoods.geojson": f"{BASE}/visualisations/neighbourhoods.geojson",
}
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        target = RAW_DIR / name
        if target.exists():
            print(f"✓ {name} already downloaded")
            continue
        print(f"↓ downloading {name} ...")
        urllib.request.urlretrieve(url, target)
    print("Done.")


if __name__ == "__main__":
    main()
