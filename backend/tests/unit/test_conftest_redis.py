import pytest

from tests import conftest
from tests.conftest import get_test_redis_url


def test_get_test_redis_url_prefers_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_REDIS_URL", "redis://ficticio:6379/14")
    monkeypatch.setattr(conftest, "dotenv_values", lambda _: {"TEST_REDIS_URL": "redis://x/1"})

    assert get_test_redis_url() == "redis://ficticio:6379/14"


def test_get_test_redis_url_falls_back_to_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_REDIS_URL", raising=False)
    monkeypatch.setattr(conftest, "dotenv_values", lambda _: {"TEST_REDIS_URL": "redis://env/13"})

    assert get_test_redis_url() == "redis://env/13"


def test_get_test_redis_url_missing_fails_with_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_REDIS_URL", raising=False)
    monkeypatch.setattr(conftest, "dotenv_values", lambda _: {})

    with pytest.raises(pytest.fail.Exception, match="docker compose up -d redis"):
        get_test_redis_url()
