import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


class OdomTfPublisher(Node):
    def __init__(self):
        super().__init__('odom_tf_publisher')
        self.tf_broadcaster = TransformBroadcaster(self)
        self.received_odom = False
        self.latest_odom = None
        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.handle_odom,
            20,
        )
        self.create_timer(5.0, self.report_waiting_for_odom)
        self.create_timer(1.0 / 30.0, self.publish_tf)

    def report_waiting_for_odom(self):
        if not self.received_odom:
            self.get_logger().warn(
                'Still waiting for /odom. Publishing a temporary identity odom -> base_link TF '
                'until odometry arrives. Check whether Gazebo spawned my_robot and whether the '
                'odometry bridge is running.'
            )

    def handle_odom(self, msg):
        self.latest_odom = msg
        if not self.received_odom:
            self.received_odom = True
            self.get_logger().info(
                'Received first /odom message, publishing odom -> base_link TF.'
            )

    def publish_tf(self):
        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'base_link'

        if self.latest_odom is None:
            transform.transform.translation.x = 0.0
            transform.transform.translation.y = 0.0
            transform.transform.translation.z = 0.0
            transform.transform.rotation.x = 0.0
            transform.transform.rotation.y = 0.0
            transform.transform.rotation.z = 0.0
            transform.transform.rotation.w = 1.0
        else:
            transform.transform.translation.x = self.latest_odom.pose.pose.position.x
            transform.transform.translation.y = self.latest_odom.pose.pose.position.y
            transform.transform.translation.z = self.latest_odom.pose.pose.position.z
            transform.transform.rotation = self.latest_odom.pose.pose.orientation

        self.tf_broadcaster.sendTransform(transform)


def main(args=None):
    rclpy.init(args=args)
    node = OdomTfPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
