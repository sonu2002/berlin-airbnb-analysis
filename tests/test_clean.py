import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from clean import classify_license, parse_bathrooms, parse_price  # noqa: E402


def test_parse_price_strips_symbols_and_commas():
    s = parse_price(pd.Series(["$1,234.00", "$97.00", None]))
    assert s.iloc[0] == 1234.0
    assert s.iloc[1] == 97.0
    assert np.isnan(s.iloc[2])


@pytest.mark.parametrize("value, expected", [
    ("03/Z/RA/011507-25", "Registration number"),
    ("Registration no. 08/z/az/010501-21 (Berlin)", "Registration number"),
    ("Legal entity name and Legal form: Example GmbH", "Business / host disclosure"),
    ("First name and Last name: Jane Doe <br/> Contact address: ...", "Business / host disclosure"),
    ("Exempt", "Exempt"),
    (None, "Missing"),
    ("   ", "Missing"),
    ("pending", "Other"),
])
def test_classify_license(value, expected):
    assert classify_license(value) == expected


@pytest.mark.parametrize("text, expected", [
    ("1 bath", 1.0), ("1.5 baths", 1.5), ("2 shared baths", 2.0), ("Half-bath", 0.5), ("Shared half-bath", 0.5),
])
def test_parse_bathrooms(text, expected):
    assert parse_bathrooms(text) == expected


def test_parse_bathrooms_missing():
    assert np.isnan(parse_bathrooms(None))
