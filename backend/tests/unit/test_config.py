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
