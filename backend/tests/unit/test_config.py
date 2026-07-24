import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_csv_is_parsed() -> None:
    settings = Settings(cors_origins="https://app.example.test,https://admin.example.test")
    assert settings.cors_origins == [
        "https://app.example.test",
        "https://admin.example.test",
    ]


def test_cors_wildcard_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(cors_origins="*")


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("gps_max_accuracy_m", 0),
        ("gps_max_speed_kmh", -1),
        ("bypass_min_match_confidence", 1.1),
        ("bypass_min_missing_run_m", 0),
        ("bypass_corridor_tolerance_m", -1),
    ],
)
def test_algorithm_thresholds_are_valid(field_name: str, value: float) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field_name: value})
