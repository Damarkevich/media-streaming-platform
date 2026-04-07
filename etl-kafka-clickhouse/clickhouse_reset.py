import logging

from clickhouse_driver import Client
from clickhouse_driver.errors import ServerException

from config.logger import configure_logging
from config.settings import settings

logger = logging.getLogger(settings.log_name)


def _cluster_clause() -> str:
    """Return optional ON CLUSTER clause based on current settings."""
    if settings.clickhouse_run_ddl_on_cluster:
        return " ON CLUSTER " + settings.clickhouse_cluster_name
    return ""


def _get_macro_value(client: Client, macro_name: str) -> str | None:
    """Read a ClickHouse macro value for the current node."""
    result = client.execute(
        "SELECT substitution FROM system.macros WHERE macro = %(macro)s LIMIT 1",
        {"macro": macro_name},
    )
    if not result:
        return None
    return str(result[0][0])


def _drop_stale_replica_znode_local(client: Client) -> None:
    """Drop stale ZooKeeper replica metadata for the current node."""
    shard = _get_macro_value(client, "shard")
    replica = _get_macro_value(client, "replica")

    if not shard or not replica:
        logger.warning("Cannot resolve shard/replica macros for stale replica cleanup.")
        return

    local_table_name = settings.clickhouse_table + "_local"
    zk_path = "/clickhouse/tables/{shard}/{database}.{table_name}".format(
        shard=shard,
        database=settings.clickhouse_local_database,
        table_name=local_table_name + "_" + settings.clickhouse_replicated_path_suffix,
    )

    query = "SYSTEM DROP REPLICA '{replica}' FROM ZKPATH '{zk_path}'".format(
        replica=replica,
        zk_path=zk_path,
    )

    try:
        client.execute(query)
        logger.warning(
            "Dropped stale replica '%s' from ZooKeeper path '%s'.",
            replica,
            zk_path,
        )
    except ServerException as error:
        logger.warning(
            "Failed to drop local stale replica '%s' from '%s': code=%s",
            replica,
            zk_path,
            error.code,
        )


def _drop_stale_replica_znode_cluster(client: Client) -> None:
    """Drop stale ZooKeeper replica metadata across all cluster hosts."""
    rows = client.execute(
        """
        SELECT shard_num, host_name
        FROM system.clusters
        WHERE cluster = %(cluster)s
        """,
        {"cluster": settings.clickhouse_cluster_name},
    )

    if not rows:
        logger.warning(
            "No rows found in system.clusters for cluster '%s'.",
            settings.clickhouse_cluster_name,
        )
        return

    local_table_name = settings.clickhouse_table + "_local"

    for shard_num, host_name in rows:
        zk_path = "/clickhouse/tables/{shard}/{database}.{table_name}".format(
            shard=shard_num,
            database=settings.clickhouse_local_database,
            table_name=local_table_name
            + "_"
            + settings.clickhouse_replicated_path_suffix,
        )

        query = "SYSTEM DROP REPLICA '{replica}' FROM ZKPATH '{zk_path}'".format(
            replica=host_name,
            zk_path=zk_path,
        )

        try:
            client.execute(query)
            logger.warning(
                "Dropped stale replica '%s' from ZooKeeper path '%s'.",
                host_name,
                zk_path,
            )
        except ServerException as error:
            logger.warning(
                "Failed to drop stale replica '%s' from '%s': code=%s",
                host_name,
                zk_path,
                error.code,
            )


def run() -> None:
    """Drop ClickHouse tables and clean stale replica metadata."""
    configure_logging()

    client = Client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
    )

    distributed_table = settings.clickhouse_database + "." + settings.clickhouse_table
    local_table = (
        settings.clickhouse_local_database + "." + settings.clickhouse_table + "_local"
    )

    cluster_clause = _cluster_clause()

    logger.warning(
        "Resetting ClickHouse tables. distributed=%s local=%s",
        distributed_table,
        local_table,
    )

    drop_distributed_query = "DROP TABLE IF EXISTS {table}{cluster_clause}".format(
        table=distributed_table,
        cluster_clause=cluster_clause,
    )
    client.execute(drop_distributed_query)

    drop_local_query = "DROP TABLE IF EXISTS {table}{cluster_clause}".format(
        table=local_table,
        cluster_clause=cluster_clause,
    )
    client.execute(drop_local_query)

    if settings.clickhouse_run_ddl_on_cluster:
        _drop_stale_replica_znode_cluster(client)
    else:
        _drop_stale_replica_znode_local(client)

    logger.info("ClickHouse reset completed.")


if __name__ == "__main__":
    run()
