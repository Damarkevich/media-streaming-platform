import os

from dotenv import load_dotenv

# Ensure environment variables from .env are loaded when this module is imported
load_dotenv()

# Redis connection defaults
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")

# Default timestamp used to initialize/reset modification timestamps in state
DEFAULT_TIMESTAMP = "0001-01-01T00:00:00.000000+00:00"

# PostgreSQL connection settings
POSTGRES_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "movies_database"),
    "user": os.getenv("POSTGRES_USER", "app"),
    "password": os.getenv("POSTGRES_PASSWORD", "123qwe"),
    "host": os.getenv("SQL_HOST", "localhost"),
    "port": int(os.getenv("SQL_PORT", "6543")),
    "options": os.getenv("SQL_OPTIONS", "-c search_path=public,content"),
}

# Batch size for PostgreSQL queries
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))

# Elasticsearch connection settings
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = os.getenv("ES_PORT", "9200")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv(
    "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOG_NAME = os.getenv("LOG_NAME", "etl_postgres_to_elasticsearch")
