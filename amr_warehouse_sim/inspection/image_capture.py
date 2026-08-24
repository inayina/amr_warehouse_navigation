from __future__ import annotations

from dataclasses import dataclass
import time


class CameraUnavailableError(RuntimeError):
    pass


class ImageTimeoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapturedImageFrame:
    topic: str
    frame_id: str
    captured_at_ns: int
    received_at_ns: int
    acquisition_started_at_ns: int
    width: int
    height: int
    encoding: str
    step: int
    data: bytes


class RosImageCapture:
    """Captures only camera frames newer than the ROS-time acquisition boundary."""

    def __init__(self, *, topic: str, use_sim_time: bool = True) -> None:
        import rclpy
        from rclpy.parameter import Parameter
        from rclpy.qos import (
            DurabilityPolicy,
            HistoryPolicy,
            QoSProfile,
            ReliabilityPolicy,
        )
        from sensor_msgs.msg import Image

        self._rclpy = rclpy
        self._topic = topic
        self._initialized_here = False
        if not rclpy.ok():
            rclpy.init(args=None)
            self._initialized_here = True
        self._node = rclpy.create_node(
            'inspection_image_capture',
            parameter_overrides=[
                Parameter('use_sim_time', Parameter.Type.BOOL, use_sim_time)
            ],
            automatically_declare_parameters_from_overrides=True,
        )
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self._latest_message = None
        self._latest_received_at_ns = 0
        self._subscription = self._node.create_subscription(
            Image,
            topic,
            self._on_image,
            qos,
        )

    @property
    def topic(self) -> str:
        return self._topic

    def _on_image(self, message) -> None:
        self._latest_message = message
        self._latest_received_at_ns = time.time_ns()

    def check_ready(self, *, timeout_sec: float) -> tuple[bool, str]:
        deadline = time.monotonic() + max(timeout_sec, 0.0)
        while True:
            if self._node.count_publishers(self._topic) > 0:
                return True, 'camera publisher available'
            if time.monotonic() >= deadline:
                return False, 'camera topic has no publisher'
            self._rclpy.spin_once(self._node, timeout_sec=0.1)

    def current_ros_time_ns(self, *, timeout_sec: float = 2.0) -> int:
        previous_ns = self._node.get_clock().now().nanoseconds
        deadline = time.monotonic() + max(timeout_sec, 0.0)
        while True:
            # The capture node is intentionally not spun while Nav2 is moving.
            # Process a fresh /clock callback before establishing the acquisition
            # boundary; otherwise get_clock() can expose the previous point's time.
            self._rclpy.spin_once(self._node, timeout_sec=0.1)
            now_ns = self._node.get_clock().now().nanoseconds
            if now_ns > 0 and (previous_ns == 0 or now_ns > previous_ns):
                return now_ns
            if time.monotonic() >= deadline:
                raise CameraUnavailableError('simulation_clock_unavailable')

    def capture_fresh(self, *, timeout_sec: float) -> CapturedImageFrame:
        ready, reason = self.check_ready(timeout_sec=min(max(timeout_sec, 0.0), 2.0))
        if not ready:
            raise CameraUnavailableError(reason)

        acquisition_started_at_ns = self.current_ros_time_ns(
            timeout_sec=min(max(timeout_sec, 0.0), 2.0)
        )
        acquisition_started_wall_ns = time.time_ns()
        deadline = time.monotonic() + max(timeout_sec, 0.0)
        while time.monotonic() <= deadline:
            self._rclpy.spin_once(self._node, timeout_sec=0.1)
            message = self._latest_message
            if message is None:
                continue
            captured_at_ns = (
                int(message.header.stamp.sec) * 1_000_000_000
                + int(message.header.stamp.nanosec)
            )
            if captured_at_ns <= acquisition_started_at_ns:
                continue
            if self._latest_received_at_ns < acquisition_started_wall_ns:
                continue
            return CapturedImageFrame(
                topic=self._topic,
                frame_id=str(message.header.frame_id),
                captured_at_ns=captured_at_ns,
                received_at_ns=self._latest_received_at_ns,
                acquisition_started_at_ns=acquisition_started_at_ns,
                width=int(message.width),
                height=int(message.height),
                encoding=str(message.encoding),
                step=int(message.step),
                data=bytes(message.data),
            )
        raise ImageTimeoutError(
            f'no image newer than acquisition start within {timeout_sec:.1f}s'
        )

    def close(self) -> None:
        self._node.destroy_subscription(self._subscription)
        self._node.destroy_node()
        if self._initialized_here and self._rclpy.ok():
            self._rclpy.shutdown()
