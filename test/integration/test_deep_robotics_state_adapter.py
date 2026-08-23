import importlib
from types import SimpleNamespace

import pytest

from amr_warehouse_sim.fleet import RobotRegistry, RobotState, seed_default_robots
from amr_warehouse_sim.integrations.deep_robotics.state_adapter import (
    DeepRoboticsDependencyError,
    DeepRoboticsStateAdapter,
    load_ros_dependencies,
)


def test_optional_integration_import_does_not_require_drdds():
    integration = importlib.import_module('amr_warehouse_sim.integrations.deep_robotics')

    assert integration.DeepRoboticsStateAdapter is DeepRoboticsStateAdapter


def test_vendor_telemetry_updates_only_liveness_fields():
    registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
    registry.mark_offline('robot_02')
    before = registry.get_robot('robot_02')
    adapter = DeepRoboticsStateAdapter(registry=registry, robot_id='robot_02')

    after = adapter.on_vendor_telemetry_received(timestamp='2026-08-23T09:00:00Z')

    assert after.last_heartbeat == '2026-08-23T09:00:00Z'
    assert after.updated_at == '2026-08-23T09:00:00Z'
    assert after.state == RobotState.OFFLINE
    assert after.current_task_id == before.current_task_id
    assert after.current_station == before.current_station
    assert after.battery == before.battery
    assert adapter.receive_count == 1


def test_vendor_telemetry_mapping_persists_heartbeat_to_sqlite(tmp_path):
    db_path = tmp_path / 'fleet.db'
    registry = RobotRegistry(db_path=db_path, auto_seed=True)
    adapter = DeepRoboticsStateAdapter(registry=registry, robot_id='robot_02')

    adapter.on_vendor_telemetry_received(timestamp='2026-08-23T09:15:00Z')
    reloaded = RobotRegistry(db_path=db_path, auto_seed=False)

    assert reloaded.get_robot('robot_02').last_heartbeat == '2026-08-23T09:15:00Z'


def test_missing_drdds_reports_actionable_optional_dependency_error(monkeypatch):
    fake_rclpy = SimpleNamespace()
    fake_node_module = SimpleNamespace(Node=object)
    fake_signals_module = SimpleNamespace(SignalHandlerOptions=object)

    def fake_import_module(name: str):
        if name == 'rclpy':
            return fake_rclpy
        if name == 'rclpy.node':
            return fake_node_module
        if name == 'rclpy.signals':
            return fake_signals_module
        if name == 'drdds.msg':
            raise ModuleNotFoundError("No module named 'drdds'")
        raise AssertionError(f'unexpected import: {name}')

    monkeypatch.setattr(
        'amr_warehouse_sim.integrations.deep_robotics.state_adapter.importlib.import_module',
        fake_import_module,
    )

    with pytest.raises(DeepRoboticsDependencyError, match='deep-robotics-msg'):
        load_ros_dependencies()
