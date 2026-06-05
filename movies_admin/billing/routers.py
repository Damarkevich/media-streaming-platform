class BillingRouter:
    """Route all billing app models to the 'billing' database alias."""

    app_label = "billing"

    def db_for_read(self, model, **hints):  # noqa: ARG002
        if model._meta.app_label == self.app_label:
            return self.app_label
        return None

    def db_for_write(self, model, **hints):  # noqa: ARG002
        if model._meta.app_label == self.app_label:
            return self.app_label
        return None

    def allow_relation(self, obj1, obj2, **hints):  # noqa: ARG002
        if self.app_label in {obj1._meta.app_label, obj2._meta.app_label}:
            return True
        return None

    def allow_migrate(self, db, app_label, **hints):  # noqa: ARG002
        # Never run Django migrations on the billing schema — managed by Alembic.
        if app_label == self.app_label:
            return False
        return None
