from types import SimpleNamespace

from django.test import SimpleTestCase

from billing.routers import BillingRouter


class BillingRouterTests(SimpleTestCase):
    def setUp(self):
        self.router = BillingRouter()

    def test_allow_migrate_blocks_billing_app_for_all_databases(self):
        assert self.router.allow_migrate("default", "billing") is False
        assert self.router.allow_migrate("billing", "billing") is False

    def test_allow_migrate_returns_none_for_other_apps(self):
        assert self.router.allow_migrate("default", "auth") is None

    def test_db_for_read_and_write_use_billing_alias(self):
        billing_model = SimpleNamespace(_meta=SimpleNamespace(app_label="billing"))
        other_model = SimpleNamespace(_meta=SimpleNamespace(app_label="auth"))

        assert self.router.db_for_read(billing_model) == "billing"
        assert self.router.db_for_write(billing_model) == "billing"
        assert self.router.db_for_read(other_model) is None
        assert self.router.db_for_write(other_model) is None
