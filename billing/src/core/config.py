from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    development_mode: bool = False

    service_name: str = "billing_service"
    service_description: str = "Stripe billing service for media platform"

    cors_origins: list[str] = ["http://localhost:3000"]

    postgres_db: str = "billing_database"
    postgres_user: str = "app"
    postgres_password: str
    postgres_db_schema: str = "billing"

    sql_host: str = "localhost"
    sql_port: int = 5432
    sql_echo: bool = False

    stripe_secret_key: str
    stripe_webhook_secret: str


settings = Settings()  # pyright: ignore[reportCallIssue]
