"""Tests for :mod:`validators.PharmacyChannelValidator`.

Covers happy-path, missing fields, empty strings, negative numbers,
duplicates, NaN, and adjustment-field allowance.
"""
import numpy as np
import pandas as pd
import pytest

from validators import PharmacyChannelValidator


@pytest.fixture
def validator() -> PharmacyChannelValidator:
    return PharmacyChannelValidator()


@pytest.fixture
def valid_record() -> dict:
    return {
        "channel_name": "retail",
        "sales_value": 100_000,
        "units_sold": 250,
        "date": "2026-01-01",
    }


class TestValidateRecord:
    def test_valid_record_passes(
        self, validator: PharmacyChannelValidator, valid_record: dict
    ) -> None:
        is_valid, errors = validator.validate_record(valid_record)
        assert is_valid
        assert errors == []

    def test_missing_required_field(
        self, validator: PharmacyChannelValidator, valid_record: dict
    ) -> None:
        incomplete = {k: v for k, v in valid_record.items() if k != "date"}
        is_valid, errors = validator.validate_record(incomplete)
        assert not is_valid
        assert any("date" in e for e in errors)

    def test_empty_string_rejected(
        self, validator: PharmacyChannelValidator, valid_record: dict
    ) -> None:
        bad = {**valid_record, "channel_name": "   "}
        is_valid, errors = validator.validate_record(bad)
        assert not is_valid
        assert any("channel_name" in e for e in errors)

    def test_none_value_rejected(
        self, validator: PharmacyChannelValidator, valid_record: dict
    ) -> None:
        bad = {**valid_record, "units_sold": None}
        is_valid, errors = validator.validate_record(bad)
        assert not is_valid
        assert any("units_sold" in e for e in errors)

    def test_negative_sales_rejected(
        self, validator: PharmacyChannelValidator, valid_record: dict
    ) -> None:
        bad = {**valid_record, "sales_value": -1.0}
        is_valid, errors = validator.validate_record(bad)
        assert not is_valid
        assert any("sales_value" in e for e in errors)

    def test_negative_adjustment_allowed(
        self, validator: PharmacyChannelValidator, valid_record: dict
    ) -> None:
        record = {**valid_record, "price_adjustment": -500}
        is_valid, errors = validator.validate_record(record)
        assert is_valid, errors

    def test_negative_change_allowed(
        self, validator: PharmacyChannelValidator, valid_record: dict
    ) -> None:
        record = {**valid_record, "yoy_change": -12.5}
        is_valid, errors = validator.validate_record(record)
        assert is_valid, errors


class TestValidateDataFrame:
    def test_clean_dataframe_passes(self, validator: PharmacyChannelValidator) -> None:
        df = pd.DataFrame(
            {
                "channel_name": ["retail", "hospital"],
                "sales_value": [100.0, 200.0],
                "units_sold": [1, 2],
                "date": ["2026-01", "2026-02"],
            }
        )
        is_valid, issues = validator.validate_dataframe(df)
        assert is_valid, issues

    def test_missing_values_surface_in_issues(
        self, validator: PharmacyChannelValidator
    ) -> None:
        df = pd.DataFrame(
            {
                "channel_name": ["retail", "hospital"],
                "sales_value": [100.0, np.nan],
                "units_sold": [1, 2],
                "date": ["2026-01", "2026-02"],
            }
        )
        is_valid, issues = validator.validate_dataframe(df)
        assert not is_valid
        assert any("missing" in i.lower() for i in issues)

    def test_duplicate_rows_flagged(
        self, validator: PharmacyChannelValidator
    ) -> None:
        df = pd.DataFrame(
            {
                "channel_name": ["retail", "retail"],
                "sales_value": [100.0, 100.0],
                "units_sold": [1, 1],
                "date": ["2026-01", "2026-01"],
            }
        )
        is_valid, issues = validator.validate_dataframe(df)
        assert not is_valid
        assert any("duplicate" in i.lower() for i in issues)

    def test_empty_dataframe_has_no_issues(
        self, validator: PharmacyChannelValidator
    ) -> None:
        # An empty DataFrame has no missing values, no duplicates, and
        # no rows to validate. The current contract returns valid=True.
        df = pd.DataFrame(
            columns=["channel_name", "sales_value", "units_sold", "date"]
        )
        is_valid, issues = validator.validate_dataframe(df)
        assert is_valid
        assert issues == []
