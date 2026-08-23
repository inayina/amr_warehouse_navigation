from __future__ import annotations

import argparse
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ...fleet.registry import RobotRecord, RobotRegistry, default_fleet_db_path

DEFAULT_ROBOT_ID = 'robot_02'
# ROS 2 maps this name to the native DDS channel ``rt/lowstate``.
DEFAULT_TOPIC = '/lowstate'
DEFAULT_QOS_DEPTH = 10


class UnitreeDependencyError(RuntimeError):
    """Raised when the optional Unitree ROS 2 runtime is unavailable."""


@dataclass(frozen=True)
class RosDependencies:
    rclpy: Any
    node_type: type
    low_state_type: type
    signal_handler_options: Any


class UnitreeStateAdapter:
    """Map one valid Unitree telemetry frame to Fleet transport liveness.

    LowState reception does not establish Fleet state, station, battery, pose,
    task progress, or execution capability.
    """

    def __init__(self, *, registry: RobotRegistry, robot_id: str = DEFAULT_ROBOT_ID):
        registry.get_robot(robot_id)
        self.registry = registry
        self.robot_id = robot_id
        self.receive_count = 0

    def on_vendor_telemetry_received(self, *, timestamp: str | None = None) -> RobotRecord:
        self.receive_count += 1
        return self.registry.record_heartbeat(
            self.robot_id,
            timestamp=timestamp,
            recover_offline=False,
        )


def load_ros_dependencies() -> RosDependencies:
    try:
        rclpy = importlib.import_module('rclpy')
        node_module = importlib.import_module('rclpy.node')
        signals_module = importlib.import_module('rclpy.signals')
    except ModuleNotFoundError as exc:
        raise UnitreeDependencyError(
            'Unitree integration requires a sourced ROS 2 rclpy environment. '
            'Source /opt/ros/<ros-distro>/setup.bash before running this optional integration.'
        ) from exc

    try:
        unitree_go_msg = importlib.import_module('unitree_go.msg')
    except ModuleNotFoundError as exc:
        raise UnitreeDependencyError(
            'Unitree integration requires the Unitree ROS 2 message packages. '
            'Source the unitree_ros2 workspace before running this optional integration.'
        ) from exc

    return RosDependencies(
        rclpy=rclpy,
        node_type=node_module.Node,
        low_state_type=unitree_go_msg.LowState,
        signal_handler_options=signals_module.SignalHandlerOptions,
    )


def create_ros_node(
    *,
    adapter: UnitreeStateAdapter,
    topic: str = DEFAULT_TOPIC,
    qos_depth: int = DEFAULT_QOS_DEPTH,
    dependencies: RosDependencies | None = None,
):
    deps = dependencies or load_ros_dependencies()

    class UnitreeStateAdapterNode(deps.node_type):
        def __init__(self):
            super().__init__('unitree_state_adapter')
            self._adapter = adapter
            self._subscription = self.create_subscription(
                deps.low_state_type,
                topic,
                self._on_low_state,
                qos_depth,
            )
            self.get_logger().info(
                f'Subscribing to {topic} for {adapter.robot_id}; '
                'telemetry updates liveness only.'
            )

        def _on_low_state(self, _message) -> None:
            record = self._adapter.on_vendor_telemetry_received()
            if self._adapter.receive_count == 1:
                self.get_logger().info(
                    f'Received first {topic} frame; {record.robot_id} '
                    f'last_heartbeat={record.last_heartbeat}; state unchanged={record.state.value}.'
                )

    return UnitreeStateAdapterNode()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Opt-in, read-only Unitree Go2 /lowstate adapter. '
            'Updates Fleet Registry heartbeat only.'
        )
    )
    parser.add_argument('--robot-id', default=DEFAULT_ROBOT_ID)
    parser.add_argument('--fleet-db', type=Path, default=default_fleet_db_path())
    parser.add_argument('--topic', default=DEFAULT_TOPIC)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        dependencies = load_ros_dependencies()
    except UnitreeDependencyError as exc:
        raise SystemExit(str(exc)) from exc

    registry = RobotRegistry(db_path=args.fleet_db, auto_seed=True)
    adapter = UnitreeStateAdapter(registry=registry, robot_id=args.robot_id)
    dependencies.rclpy.init(
        args=None,
        signal_handler_options=dependencies.signal_handler_options.NO,
    )
    node = create_ros_node(
        adapter=adapter,
        topic=args.topic,
        dependencies=dependencies,
    )
    try:
        dependencies.rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        print(f'Unitree adapter received {adapter.receive_count} frame(s).')
        node.destroy_node()
        dependencies.rclpy.try_shutdown()


if __name__ == '__main__':
    main()
