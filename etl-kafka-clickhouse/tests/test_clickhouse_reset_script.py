from unittest.mock import Mock, patch

from clickhouse_driver.errors import ServerException

import clickhouse_reset


def _server_exception(code: int) -> ServerException:
    exc = ServerException.__new__(ServerException)
    exc.code = code
    return exc


def test_clickhouse_reset_drops_tables_and_cluster_replicas() -> None:
    fake_client = Mock()

    fake_client.execute.side_effect = [
        None,
        None,
        [(1, "clickhouse-node1"), (2, "clickhouse-node3")],
        None,
        None,
    ]

    with patch("clickhouse_reset.configure_logging"), patch(
        "clickhouse_reset.Client", return_value=fake_client
    ), patch.object(clickhouse_reset.settings, "clickhouse_run_ddl_on_cluster", True), patch.object(
        clickhouse_reset.settings, "clickhouse_cluster_name", "company_cluster"
    ):
        clickhouse_reset.run()

    executed = [call.args[0] for call in fake_client.execute.call_args_list]

    assert any("DROP TABLE IF EXISTS events.user_events ON CLUSTER company_cluster" in query for query in executed)
    assert any("DROP TABLE IF EXISTS shard.user_events_local ON CLUSTER company_cluster" in query for query in executed)
    assert any("SELECT shard_num, host_name" in query for query in executed)
    assert any("SYSTEM DROP REPLICA 'clickhouse-node1'" in query for query in executed)
    assert any("SYSTEM DROP REPLICA 'clickhouse-node3'" in query for query in executed)


def test_clickhouse_reset_local_macro_cleanup_path() -> None:
    fake_client = Mock()

    fake_client.execute.side_effect = [
        None,
        None,
        [("1",)],
        [("clickhouse-node1",)],
        _server_exception(305),
    ]

    with patch("clickhouse_reset.configure_logging"), patch(
        "clickhouse_reset.Client", return_value=fake_client
    ), patch.object(clickhouse_reset.settings, "clickhouse_run_ddl_on_cluster", False):
        clickhouse_reset.run()

    executed = [call.args[0] for call in fake_client.execute.call_args_list]

    assert any("SELECT substitution FROM system.macros" in query for query in executed)
    assert any("SYSTEM DROP REPLICA 'clickhouse-node1'" in query for query in executed)
