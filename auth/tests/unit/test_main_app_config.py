from src.core.config import settings
from src.main import _get_docs_url, _get_openapi_url


def test_docs_and_openapi_urls_enabled_in_development_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "development_mode", True)

    assert _get_docs_url() == "/api/auth/docs"
    assert _get_openapi_url() == "/api/auth/openapi.json"


def test_docs_and_openapi_urls_disabled_outside_development_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "development_mode", False)

    assert _get_docs_url() is None
    assert _get_openapi_url() is None
