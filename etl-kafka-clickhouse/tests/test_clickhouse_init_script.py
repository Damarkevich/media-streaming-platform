from unittest.mock import Mock, patch

import clickhouse_init


def test_clickhouse_init_runs_expected_ddl_sequence() -> None:
    fake_client = Mock()

    with patch("clickhouse_init.configure_logging"), patch(
        "clickhouse_init.Client", return_value=fake_client
    ):
        clickhouse_init.run()

    executed = [call.args[0] for call in fake_client.execute.call_args_list]

    assert any("CREATE DATABASE IF NOT EXISTS events" in query for query in executed)
    assert any("CREATE DATABASE IF NOT EXISTS shard" in query for query in executed)
    assert any("CREATE TABLE IF NOT EXISTS shard.user_events_local" in query for query in executed)
    assert any("ReplicatedReplacingMergeTree" in query for query in executed)
    assert any("CREATE TABLE IF NOT EXISTS events.user_events" in query for query in executed)
    assert any("ENGINE = Distributed" in query for query in executed)


def test_clickhouse_init_uses_cluster_clause_when_enabled() -> None:
    fake_client = Mock()

    with patch("clickhouse_init.configure_logging"), patch(
        "clickhouse_init.Client", return_value=fake_client
    ), patch.object(clickhouse_init.settings, "clickhouse_run_ddl_on_cluster", True), patch.object(
        clickhouse_init.settings, "clickhouse_cluster_name", "company_cluster"
    ):
        clickhouse_init.run()

    executed = [call.args[0] for call in fake_client.execute.call_args_list]
    assert any("ON CLUSTER company_cluster" in query for query in executed)
