import importlib
from types import SimpleNamespace

import pytest

from amr_warehouse_sim.fleet import RobotRegistry, RobotState, seed_default_robots
from amr_warehouse_sim.integrations.deep_robotics.state_adapter import (
    DeepRoboticsStateAdapter,
)
from amr_warehouse_sim.integrations.unitree.state_adapter import (
    DEFAULT_QOS_DEPTH,
    DEFAULT_TOPIC,
    RosDependencies,
    UnitreeDependencyError,
    UnitreeStateAdapter,
    create_ros_node,
    load_ros_dependencies,
)


def test_optional_integration_import_does_not_require_unitree_runtime():
    integration = importlib.import_module('amr_warehouse_sim.integrations.unitree')

    assert integration.UnitreeStateAdapter is UnitreeStateAdapter


def test_vendor_telemetry_updates_only_liveness_fields():
    registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
    registry.mark_offline('robot_02')
    before = registry.get_robot('robot_02')
    adapter = UnitreeStateAdapter(registry=registry, robot_id='robot_02')

    after = adapter.on_vendor_telemetry_received(timestamp='2026-08-23T09:00:00Z')

    assert after.last_heartbeat == '2026-08-23T09:00:00Z'
    assert after.updated_at == '2026-08-23T09:00:00Z'
    assert after.state == RobotState.OFFLINE
    assert after.current_task_id == before.current_task_id
    assert after.current_station == before.current_station
    assert after.battery == before.battery
    assert adapter.receive_count == 1


def test_vendor_telemetry_preserves_active_task_and_business_fields():
    registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
    registry.assign_task('robot_02', 802)
    registry.mark_busy('robot_02')
    registry.set_current_station('robot_02', 'station_a')
    registry.mark_offline('robot_02')
    before = registry.get_robot('robot_02')
    adapter = UnitreeStateAdapter(registry=registry, robot_id='robot_02')

    after = adapter.on_vendor_telemetry_received(timestamp='2026-08-23T09:05:00Z')

    assert after.state == RobotState.OFFLINE
    assert after.current_task_id == 802
    assert after.current_station == 'station_a'
    assert after.battery == before.battery


def test_vendor_telemetry_mapping_persists_heartbeat_to_sqlite(tmp_path):
    db_path = tmp_path / 'fleet.db'
    registry = RobotRegistry(db_path=db_path, auto_seed=True)
    adapter = UnitreeStateAdapter(registry=registry, robot_id='robot_02')

    adapter.on_vendor_telemetry_received(timestamp='2026-08-23T09:15:00Z')
    reloaded = RobotRegistry(db_path=db_path, auto_seed=False)

    assert reloaded.get_robot('robot_02').last_heartbeat == '2026-08-23T09:15:00Z'


def test_missing_unitree_message_package_reports_actionable_error(monkeypatch):
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
        if name == 'unitree_go.msg':
            raise ModuleNotFoundError("No module named 'unitree_go'")
        raise AssertionError(f'unexpected import: {name}')

    monkeypatch.setattr(
        'amr_warehouse_sim.integrations.unitree.state_adapter.importlib.import_module',
        fake_import_module,
    )

    with pytest.raises(UnitreeDependencyError, match='Source the unitree_ros2 workspace'):
        load_ros_dependencies()


def test_ros_node_uses_audited_lowstate_topic_type_and_depth():
    subscription = {}

    class FakeLogger:
        def info(self, _message):
            pass

    class FakeNode:
        def __init__(self, name):
            subscription['node_name'] = name

        def create_subscription(self, message_type, topic, callback, qos_depth):
            subscription.update(
                message_type=message_type,
                topic=topic,
                callback=callback,
                qos_depth=qos_depth,
            )
            return object()

        def get_logger(self):
            return FakeLogger()

    class FakeLowState:
        pass

    registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
    adapter = UnitreeStateAdapter(registry=registry, robot_id='robot_02')
    dependencies = RosDependencies(
        rclpy=SimpleNamespace(),
        node_type=FakeNode,
        low_state_type=FakeLowState,
        signal_handler_options=SimpleNamespace(),
    )

    create_ros_node(adapter=adapter, dependencies=dependencies)

    assert subscription['node_name'] == 'unitree_state_adapter'
    assert subscription['message_type'] is FakeLowState
    assert subscription['topic'] == DEFAULT_TOPIC == '/lowstate'
    assert subscription['qos_depth'] == DEFAULT_QOS_DEPTH == 10


def test_vendor_adapters_share_internal_liveness_semantic():
    timestamp = '2026-08-23T09:30:00Z'
    records = []

    for adapter_type in (DeepRoboticsStateAdapter, UnitreeStateAdapter):
        registry = RobotRegistry(robots=seed_default_robots(timestamp='2026-08-23T08:00:00Z'))
        registry.mark_offline('robot_02')
        before = registry.get_robot('robot_02')
        after = adapter_type(
            registry=registry,
            robot_id='robot_02',
        ).on_vendor_telemetry_received(timestamp=timestamp)
        records.append((before, after))

    for before, after in records:
        assert after.last_heartbeat == timestamp
        assert after.state == before.state == RobotState.OFFLINE
        assert after.current_task_id == before.current_task_id
        assert after.current_station == before.current_station
        assert after.battery == before.battery
