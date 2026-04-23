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
        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.publish_tf,
            20,
        )
        self.create_timer(5.0, self.report_waiting_for_odom)

    def report_waiting_for_odom(self):
        if not self.received_odom:
            self.get_logger().warn(
                'Still waiting for /odom. '
                'Check whether Gazebo spawned my_robot and whether the odometry bridge is running.'
            )

    def publish_tf(self, msg):
        if not self.received_odom:
            self.received_odom = True
            self.get_logger().info(
                'Received first /odom message, publishing odom -> base_link TF.'
            )
        transform = TransformStamped()
        transform.header.stamp = msg.header.stamp
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'base_link'
        transform.transform.translation.x = msg.pose.pose.position.x
        transform.transform.translation.y = msg.pose.pose.position.y
        transform.transform.translation.z = msg.pose.pose.position.z
        transform.transform.rotation = msg.pose.pose.orientation
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
