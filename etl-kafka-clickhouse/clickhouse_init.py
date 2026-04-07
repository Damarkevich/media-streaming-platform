import logging

from clickhouse_driver import Client

from config.logger import configure_logging
from config.settings import settings

logger = logging.getLogger(settings.log_name)


def _cluster_clause() -> str:
    """Return optional ON CLUSTER clause based on current settings."""
    if settings.clickhouse_run_ddl_on_cluster:
        return " ON CLUSTER " + settings.clickhouse_cluster_name
    return ""


def run() -> None:
    """Create ClickHouse databases and local/distributed tables."""
    configure_logging()

    client = Client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
    )

    cluster_clause = _cluster_clause()

    distributed_database = settings.clickhouse_database
    distributed_table_name = settings.clickhouse_table
    distributed_table = distributed_database + "." + distributed_table_name

    local_database = settings.clickhouse_local_database
    local_table_name = distributed_table_name + "_local"
    local_table = local_database + "." + local_table_name

    create_distributed_db_query = (
        "CREATE DATABASE IF NOT EXISTS {db}{cluster_clause}".format(
            db=distributed_database,
            cluster_clause=cluster_clause,
        )
    )
    client.execute(create_distributed_db_query)

    if local_database != distributed_database:
        create_local_db_query = (
            "CREATE DATABASE IF NOT EXISTS {db}{cluster_clause}".format(
                db=local_database,
                cluster_clause=cluster_clause,
            )
        )
        client.execute(create_local_db_query)

    local_query = """
        CREATE TABLE IF NOT EXISTS {table}{cluster_clause} (
            event_date Date DEFAULT toDate(server_timestamp),
            event_timestamp DateTime,
            server_timestamp DateTime,

            event_id UUID,
            user_id UUID,
            session_id UUID,
            movie_id Nullable(UUID),

            event_type LowCardinality(String),

            context String,
            payload String

        )
        ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{{shard}}/{database}.{table_name}', '{{replica}}', server_timestamp)
        PARTITION BY toYYYYMM(event_date)
        ORDER BY (event_id, user_id, event_timestamp)
        TTL event_date + INTERVAL 12 MONTH DELETE
        """.format(
        table=local_table,
        cluster_clause=cluster_clause,
        database=local_database,
        table_name=local_table_name + "_" + settings.clickhouse_replicated_path_suffix,
    )

    client.execute(local_query)

    distributed_query = """
        CREATE TABLE IF NOT EXISTS {distributed_table}{cluster_clause}
        AS {local_table}
        ENGINE = Distributed('{cluster_name}', '{local_database}', '{local_table_name}', {sharding_key})
        """.format(
        distributed_table=distributed_table,
        cluster_clause=cluster_clause,
        local_table=local_table,
        cluster_name=settings.clickhouse_cluster_name,
        local_database=local_database,
        local_table_name=local_table_name,
        sharding_key=settings.clickhouse_sharding_key,
    )
    client.execute(distributed_query)

    logger.info(
        "ClickHouse init completed. local=%s distributed=%s",
        local_table,
        distributed_table,
    )


if __name__ == "__main__":
    run()
