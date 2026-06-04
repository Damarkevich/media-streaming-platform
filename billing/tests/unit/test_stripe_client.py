import stripe

from src.services.stripe_client import configure_stripe_client


def test_configure_stripe_client_sets_api_key(monkeypatch) -> None:
    monkeypatch.setattr(stripe, "api_key", None)

    api_key = configure_stripe_client()

    assert stripe.api_key == api_key
    assert api_key == "sk_test_123"
