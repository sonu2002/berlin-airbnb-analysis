"""Train and evaluate nightly-price models, then export the best one for the web dashboard.

Only features a host could type into a form are used, so the same model powers the
in-browser price estimator on the live dashboard.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "listings_clean.csv"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
SEED = 42

CATEGORICAL = ["district", "room_type"]
NUMERIC = ["accommodates", "bedrooms", "bathrooms", "minimum_nights", "amenities_count", "review_score"]
BOOLEAN = ["shared_bath", "superhost"]
TARGET = "price"


def load_features():
    df = pd.read_csv(DATA)
    df = df[df["room_type"].isin(["Entire home/apt", "Private room"])].copy()  # other types < 2 % of market
    df["bedrooms"] = df["bedrooms"].fillna(df["bedrooms"].median()).clip(0, 6)
    df["bathrooms"] = df["bathrooms"].fillna(1).clip(0, 4)
    df["accommodates"] = df["accommodates"].clip(1, 12)
    df["minimum_nights"] = df["minimum_nights"].fillna(df["minimum_nights"].median()).clip(1, 90)
    df["review_score"] = df["review_score"].fillna(df["review_score"].median())
    for col in BOOLEAN:
        df[col] = df[col].astype(int)
    return df


def preprocessor(scale: bool):
    numeric = [("num", StandardScaler() if scale else "passthrough", NUMERIC + BOOLEAN)]
    return ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL)] + numeric
    )


def main() -> None:
    df = load_features()
    X, y = df[CATEGORICAL + NUMERIC + BOOLEAN], np.log(df[TARGET])   # log target: prices are right-skewed
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    candidates = {
        "Baseline (median)": Pipeline([("prep", preprocessor(False)), ("model", DummyRegressor(strategy="median"))]),
        "Ridge regression": Pipeline([("prep", preprocessor(True)), ("model", Ridge(alpha=1.0))]),
        "Random forest": Pipeline([("prep", preprocessor(False)),
                                   ("model", RandomForestRegressor(n_estimators=300, min_samples_leaf=3, n_jobs=-1, random_state=SEED))]),
        "Gradient boosting": Pipeline([("prep", preprocessor(False)),
                                       ("model", GradientBoostingRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                                                                           subsample=0.8, random_state=SEED))]),
    }

    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)
    rows = []
    for name, pipe in candidates.items():
        cv_r2 = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="r2")
        pipe.fit(X_train, y_train)
        pred = np.exp(pipe.predict(X_test))
        rows.append({
            "model": name,
            "cv_r2_log": round(cv_r2.mean(), 3),
            "test_r2_log": round(r2_score(y_test, np.log(pred)), 3),
            "test_mae_eur": round(mean_absolute_error(np.exp(y_test), pred), 1),
            "test_median_ae_eur": round(float(np.median(np.abs(np.exp(y_test) - pred))), 1),
        })
        print(rows[-1])
    results = pd.DataFrame(rows)
    REPORTS.mkdir(exist_ok=True)
    results.to_csv(REPORTS / "model_comparison.csv", index=False)

    best = candidates["Gradient boosting"]
    imp = permutation_importance(best, X_test, y_test, n_repeats=10, random_state=SEED, scoring="r2")
    importance = (pd.DataFrame({"feature": X.columns, "importance": imp.importances_mean})
                  .sort_values("importance", ascending=False))
    importance.to_csv(REPORTS / "feature_importance.csv", index=False)

    test_out = pd.DataFrame({"actual": np.exp(y_test), "predicted": np.exp(best.predict(X_test))})
    test_out.to_csv(REPORTS / "test_predictions.csv", index=False)

    export_for_browser(best, X.columns.tolist(), df, results)


def export_for_browser(pipe, raw_columns, df, results):
    """Serialise the fitted gradient-boosting trees to JSON so the dashboard can predict in JavaScript."""
    prep, gbr = pipe.named_steps["prep"], pipe.named_steps["model"]
    feature_names = prep.get_feature_names_out().tolist()
    trees = []
    for est in gbr.estimators_[:, 0]:
        t = est.tree_
        trees.append({
            "f": t.feature.tolist(), "t": np.round(t.threshold, 6).tolist(),
            "l": t.children_left.tolist(), "r": t.children_right.tolist(),
            "v": np.round(t.value[:, 0, 0], 6).tolist(),
        })
    init = float(gbr.init_.constant_[0][0]) if hasattr(gbr.init_, "constant_") else float(gbr._raw_predict_init(np.zeros((1, len(feature_names))))[0][0])
    gb_row = results[results["model"] == "Gradient boosting"].iloc[0]
    model = {
        "description": "GradientBoostingRegressor on log(price); prediction = exp(init + lr * sum(tree outputs))",
        "features": feature_names,
        "categories": {c: sorted(df[c].unique().tolist()) for c in CATEGORICAL},
        "init": init, "learning_rate": gbr.learning_rate, "trees": trees,
        "metrics": {"test_mae_eur": float(gb_row["test_mae_eur"]), "test_r2_log": float(gb_row["test_r2_log"])},
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "model.json").write_text(json.dumps(model, separators=(",", ":")))
    # A few reference predictions to verify the JavaScript implementation matches Python exactly
    sample = df[raw_columns].sample(25, random_state=SEED)
    checks = [{"input": row.to_dict(), "price": float(np.exp(pipe.predict(row.to_frame().T.astype(sample.dtypes.to_dict()))[0]))}
              for _, row in sample.iterrows()]
    (REPORTS / "js_check_cases.json").write_text(json.dumps(checks, default=float))
    print(f"exported {len(trees)} trees → docs/model.json")


if __name__ == "__main__":
    main()
