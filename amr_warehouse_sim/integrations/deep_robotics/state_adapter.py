from __future__ import annotations

import argparse
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ...fleet.registry import RobotRecord, RobotRegistry, default_fleet_db_path

DEFAULT_ROBOT_ID = 'robot_02'
DEFAULT_TOPIC = '/JOINTS_DATA'
DEFAULT_QOS_DEPTH = 10


class DeepRoboticsDependencyError(RuntimeError):
    """Raised when the optional ROS/vendor runtime is not available."""


@dataclass(frozen=True)
class RosDependencies:
    rclpy: Any
    node_type: type
    joints_type: type
    signal_handler_options: Any


class DeepRoboticsStateAdapter:
    """Map one valid vendor telemetry frame to Fleet transport liveness.

    This mapping deliberately does not infer IDLE/BUSY, station, battery, pose,
    task completion, or execution capability from joint telemetry.
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
        raise DeepRoboticsDependencyError(
            'Deep Robotics integration requires a sourced ROS 2 rclpy environment. '
            'Source /opt/ros/<ros-distro>/setup.bash before running this optional integration.'
        ) from exc

    try:
        drdds_msg = importlib.import_module('drdds.msg')
    except ModuleNotFoundError as exc:
        raise DeepRoboticsDependencyError(
            'Deep Robotics integration requires the ROS 2 package `drdds`. '
            'Install/source DeepRoboticsLab/deep-robotics-msg before running this '
            'optional integration.'
        ) from exc

    return RosDependencies(
        rclpy=rclpy,
        node_type=node_module.Node,
        joints_type=drdds_msg.Joints,
        signal_handler_options=signals_module.SignalHandlerOptions,
    )


def create_ros_node(
    *,
    adapter: DeepRoboticsStateAdapter,
    topic: str = DEFAULT_TOPIC,
    qos_depth: int = DEFAULT_QOS_DEPTH,
    dependencies: RosDependencies | None = None,
):
    deps = dependencies or load_ros_dependencies()

    class DeepRoboticsStateAdapterNode(deps.node_type):
        def __init__(self):
            super().__init__('deep_robotics_state_adapter')
            self._adapter = adapter
            self._subscription = self.create_subscription(
                deps.joints_type,
                topic,
                self._on_joints_data,
                qos_depth,
            )
            self.get_logger().info(
                f'Subscribing to {topic} for {adapter.robot_id}; '
                'telemetry updates liveness only.'
            )

        def _on_joints_data(self, _message) -> None:
            record = self._adapter.on_vendor_telemetry_received()
            if self._adapter.receive_count == 1:
                self.get_logger().info(
                    f'Received first {topic} frame; {record.robot_id} '
                    f'last_heartbeat={record.last_heartbeat}; state unchanged={record.state.value}.'
                )

    return DeepRoboticsStateAdapterNode()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Opt-in, read-only DR02 Pro /JOINTS_DATA adapter. '
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
    except DeepRoboticsDependencyError as exc:
        raise SystemExit(str(exc)) from exc

    registry = RobotRegistry(db_path=args.fleet_db, auto_seed=True)
    adapter = DeepRoboticsStateAdapter(registry=registry, robot_id=args.robot_id)
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
        print(f'Deep Robotics adapter received {adapter.receive_count} frame(s).')
        node.destroy_node()
        dependencies.rclpy.try_shutdown()


if __name__ == '__main__':
    main()
