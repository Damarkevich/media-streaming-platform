import importlib
import sys

MODULE_NAME = "src.main"
CONFIG_MODULE_NAME = "src.core.config"


def _load_app_with_env(monkeypatch, development_mode: bool):
    monkeypatch.setenv("DEVELOPMENT_MODE", str(development_mode).lower())

    # Force config and app re-import so settings are rebuilt from env vars.
    sys.modules.pop(CONFIG_MODULE_NAME, None)
    sys.modules.pop(MODULE_NAME, None)
    main_module = importlib.import_module(MODULE_NAME)
    return main_module.app


def _has_request_id_middleware(app) -> bool:
    return any(
        getattr(middleware.kwargs.get("dispatch"), "__name__", "")
        == "request_id_middleware"
        for middleware in app.user_middleware
    )


def test_request_id_middleware_enabled_when_development_mode_is_false(monkeypatch):
    app = _load_app_with_env(monkeypatch, development_mode=False)

    assert _has_request_id_middleware(app)


def test_request_id_middleware_disabled_in_development_mode(monkeypatch):
    app = _load_app_with_env(monkeypatch, development_mode=True)

    assert not _has_request_id_middleware(app)
