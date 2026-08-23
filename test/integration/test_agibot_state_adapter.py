import importlib
from pathlib import Path
import sys

import pytest

from amr_warehouse_sim.fleet import RobotRegistry, RobotState, seed_default_robots
from amr_warehouse_sim.integrations.agibot.state_adapter import (
    AgibotDependencyError,
    AgibotProbeProcessError,
    AgibotStateAdapter,
    run_probe_process,
)
from amr_warehouse_sim.integrations.deep_robotics.state_adapter import (
    DeepRoboticsStateAdapter,
)
from amr_warehouse_sim.integrations.unitree.state_adapter import UnitreeStateAdapter


VALID_EVENT = (
    '{"event":"telemetry","vendor":"agibot",'
    '"model":"d1_maxpro","source":"GetRobotStatus"}'
)


def test_optional_integration_import_does_not_require_vendor_sdk():
    integration = importlib.import_module('amr_warehouse_sim.integrations.agibot')

    assert integration.AgibotStateAdapter is AgibotStateAdapter


def test_probe_telemetry_updates_only_liveness_fields():
    registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
    registry.mark_offline('robot_02')
    before = registry.get_robot('robot_02')
    adapter = AgibotStateAdapter(registry=registry, robot_id='robot_02')

    after = adapter.on_probe_line(VALID_EVENT, timestamp='2026-08-23T10:00:00Z')

    assert after is not None
    assert after.last_heartbeat == '2026-08-23T10:00:00Z'
    assert after.updated_at == '2026-08-23T10:00:00Z'
    assert after.state == before.state == RobotState.OFFLINE
    assert after.current_task_id == before.current_task_id
    assert after.current_station == before.current_station
    assert after.battery == before.battery
    assert adapter.receive_count == 1


def test_probe_telemetry_preserves_active_task_station_and_battery():
    registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
    registry.assign_task('robot_02', 903)
    registry.mark_busy('robot_02')
    registry.set_current_station('robot_02', 'station_b')
    registry.mark_offline('robot_02')
    before = registry.get_robot('robot_02')
    adapter = AgibotStateAdapter(registry=registry, robot_id='robot_02')

    after = adapter.on_probe_line(VALID_EVENT, timestamp='2026-08-23T10:05:00Z')

    assert after is not None
    assert after.state == RobotState.OFFLINE
    assert after.current_task_id == 903
    assert after.current_station == 'station_b'
    assert after.battery == before.battery


def test_probe_telemetry_persists_heartbeat_to_sqlite(tmp_path):
    db_path = tmp_path / 'fleet.db'
    registry = RobotRegistry(db_path=db_path, auto_seed=True)
    adapter = AgibotStateAdapter(registry=registry, robot_id='robot_02')

    adapter.on_probe_line(VALID_EVENT, timestamp='2026-08-23T10:10:00Z')
    reloaded = RobotRegistry(db_path=db_path, auto_seed=False)

    assert reloaded.get_robot('robot_02').last_heartbeat == '2026-08-23T10:10:00Z'


@pytest.mark.parametrize(
    'line',
    [
        '',
        'not-json',
        '[]',
        '{"event":"ready","vendor":"agibot","model":"d1_maxpro"}',
        '{"event":"telemetry","vendor":"other","model":"d1_maxpro"}',
        '{"event":"telemetry","vendor":"agibot","model":"other"}',
    ],
)
def test_malformed_or_foreign_probe_event_is_ignored_safely(line):
    registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
    before = registry.get_robot('robot_02')
    adapter = AgibotStateAdapter(registry=registry, robot_id='robot_02')

    result = adapter.on_probe_line(line)

    assert result is None
    assert adapter.receive_count == 0
    assert adapter.rejected_count == 1
    assert registry.get_robot('robot_02') == before


def test_missing_probe_executable_reports_actionable_error(tmp_path):
    registry = RobotRegistry(robots=seed_default_robots())
    adapter = AgibotStateAdapter(registry=registry, robot_id='robot_02')
    missing_probe = tmp_path / 'agibot_d1_maxpro_state_probe'

    with pytest.raises(AgibotDependencyError, match='Build the vendor-side probe'):
        run_probe_process(
            adapter=adapter,
            probe_executable=missing_probe,
        )


def test_mock_probe_jsonl_contract_updates_heartbeat():
    registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
    adapter = AgibotStateAdapter(registry=registry, robot_id='robot_02')

    result = run_probe_process(
        adapter=adapter,
        probe_executable=Path(sys.executable),
        probe_args=('-c', f'print({VALID_EVENT!r})'),
    )

    assert result.returncode == 0
    assert result.telemetry_events == 1
    assert result.rejected_events == 0
    assert registry.get_robot('robot_02').last_heartbeat != '2026-08-23T08:00:00Z'


def test_clean_probe_eof_before_telemetry_is_reported_clearly():
    registry = RobotRegistry(robots=seed_default_robots())
    adapter = AgibotStateAdapter(registry=registry, robot_id='robot_02')

    with pytest.raises(AgibotProbeProcessError, match='EOF before any valid telemetry'):
        run_probe_process(
            adapter=adapter,
            probe_executable=Path(sys.executable),
            probe_args=('-c', 'pass'),
        )


def test_probe_process_death_reports_exit_code():
    registry = RobotRegistry(robots=seed_default_robots())
    adapter = AgibotStateAdapter(registry=registry, robot_id='robot_02')

    with pytest.raises(AgibotProbeProcessError, match='exited with code 7'):
        run_probe_process(
            adapter=adapter,
            probe_executable=Path(sys.executable),
            probe_args=('-c', 'raise SystemExit(7)'),
        )


def test_three_vendor_adapters_share_internal_liveness_semantic():
    timestamp = '2026-08-23T10:30:00Z'

    for adapter_type in (
        DeepRoboticsStateAdapter,
        UnitreeStateAdapter,
        AgibotStateAdapter,
    ):
        registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
        registry.mark_offline('robot_02')
        before = registry.get_robot('robot_02')
        after = adapter_type(
            registry=registry,
            robot_id='robot_02',
        ).on_vendor_telemetry_received(timestamp=timestamp)

        assert after.last_heartbeat == timestamp
        assert after.state == before.state == RobotState.OFFLINE
        assert after.current_task_id == before.current_task_id
        assert after.current_station == before.current_station
        assert after.battery == before.battery
