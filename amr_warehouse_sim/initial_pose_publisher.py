import argparse
import math
import time

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.node import Node


DEFAULT_COVARIANCE_XY = 0.25
DEFAULT_COVARIANCE_YAW = 0.06853891945200942
PRESETS = {
    'start_zone': {
        'x': 0.0,
        'y': 0.0,
        'yaw': 0.0,
        'description': (
            'Robot spawn pose and green start-zone center in '
            'worlds/warehouse_full.world.'
        ),
    },
}


def create_parser():
    parser = argparse.ArgumentParser(
        description='Publish an AMCL initial pose to /initialpose.'
    )
    parser.add_argument(
        '--preset',
        choices=sorted(PRESETS.keys()),
        help='Named initial-pose preset based on the current map / world baseline.',
    )
    parser.add_argument('--x', type=float, help='Initial pose X in map frame.')
    parser.add_argument('--y', type=float, help='Initial pose Y in map frame.')
    parser.add_argument(
        '--yaw',
        type=float,
        help='Initial yaw in radians in map frame.',
    )
    parser.add_argument(
        '--topic',
        default='/initialpose',
        help='Topic to publish the initial pose to.',
    )
    parser.add_argument(
        '--frame-id',
        default='map',
        help='Frame ID for the initial pose message.',
    )
    parser.add_argument(
        '--covariance-xy',
        type=float,
        default=DEFAULT_COVARIANCE_XY,
        help='Covariance for X and Y position.',
    )
    parser.add_argument(
        '--covariance-yaw',
        type=float,
        default=DEFAULT_COVARIANCE_YAW,
        help='Covariance for yaw.',
    )
    parser.add_argument(
        '--count',
        type=int,
        default=10,
        help='Number of times to publish the initial pose.',
    )
    parser.add_argument(
        '--interval',
        type=float,
        default=0.2,
        help='Seconds to wait between repeated publications.',
    )
    parser.add_argument(
        '--wait-for-subscribers',
        type=float,
        default=5.0,
        help='Seconds to wait for at least one /initialpose subscriber before publishing.',
    )
    return parser


def yaw_to_quaternion(yaw):
    half_yaw = yaw / 2.0
    return (
        0.0,
        0.0,
        math.sin(half_yaw),
        math.cos(half_yaw),
    )


def resolve_pose_args(args, parser):
    pose = {}
    if args.preset is not None:
        pose.update(
            {
                'x': PRESETS[args.preset]['x'],
                'y': PRESETS[args.preset]['y'],
                'yaw': PRESETS[args.preset]['yaw'],
            }
        )

    for key in ('x', 'y', 'yaw'):
        value = getattr(args, key)
        if value is not None:
            pose[key] = value

    missing = [key for key in ('x', 'y', 'yaw') if key not in pose]
    if missing:
        parser.error(
            'either provide --preset or specify all of --x, --y, and --yaw; '
            f'missing: {", ".join(missing)}'
        )

    args.x = pose['x']
    args.y = pose['y']
    args.yaw = pose['yaw']
    return args


def build_initial_pose_message(
    *,
    x,
    y,
    yaw,
    frame_id='map',
    covariance_xy=DEFAULT_COVARIANCE_XY,
    covariance_yaw=DEFAULT_COVARIANCE_YAW,
):
    msg = PoseWithCovarianceStamped()
    msg.header.frame_id = frame_id
    msg.pose.pose.position.x = x
    msg.pose.pose.position.y = y
    msg.pose.pose.position.z = 0.0

    qx, qy, qz, qw = yaw_to_quaternion(yaw)
    msg.pose.pose.orientation.x = qx
    msg.pose.pose.orientation.y = qy
    msg.pose.pose.orientation.z = qz
    msg.pose.pose.orientation.w = qw

    msg.pose.covariance[0] = covariance_xy
    msg.pose.covariance[7] = covariance_xy
    msg.pose.covariance[35] = covariance_yaw
    return msg


class InitialPosePublisher(Node):
    def __init__(self, args):
        super().__init__('initial_pose_publisher')
        self.args = args
        self.publisher = self.create_publisher(PoseWithCovarianceStamped, args.topic, 10)

    def wait_for_subscribers(self):
        deadline = time.monotonic() + max(self.args.wait_for_subscribers, 0.0)
        while time.monotonic() < deadline:
            if self.publisher.get_subscription_count() > 0:
                self.get_logger().info(
                    f'Found {self.publisher.get_subscription_count()} subscriber(s) on '
                    f'{self.args.topic}.'
                )
                return True
            rclpy.spin_once(self, timeout_sec=0.1)

        self.get_logger().warn(
            f'No subscribers detected on {self.args.topic} within '
            f'{self.args.wait_for_subscribers:.1f}s. Publishing anyway.'
        )
        return False

    def publish_initial_pose(self):
        msg = build_initial_pose_message(
            x=self.args.x,
            y=self.args.y,
            yaw=self.args.yaw,
            frame_id=self.args.frame_id,
            covariance_xy=self.args.covariance_xy,
            covariance_yaw=self.args.covariance_yaw,
        )

        self.wait_for_subscribers()

        for index in range(self.args.count):
            msg.header.stamp = self.get_clock().now().to_msg()
            self.publisher.publish(msg)
            self.get_logger().info(
                f'Published initial pose {index + 1}/{self.args.count}: '
                f'x={self.args.x:.3f}, y={self.args.y:.3f}, yaw={self.args.yaw:.3f} rad, '
                f'frame={self.args.frame_id}'
            )
            if index + 1 < self.args.count:
                time.sleep(max(self.args.interval, 0.0))


def main(args=None):
    parser = create_parser()
    parsed_args = resolve_pose_args(parser.parse_args(args=args), parser)

    rclpy.init(args=None)
    node = InitialPosePublisher(parsed_args)
    try:
        node.publish_initial_pose()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
