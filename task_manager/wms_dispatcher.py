import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
import json

class WMSDispatcher(Node):
    def __init__(self):
        super().__init__('wms_dispatcher')
        self.declare_parameter('robot_names', ['robot1', 'robot2'])
        self.robot_names = self.get_parameter('robot_names').value

        # 为每个机器人创建 action client
        self.clients = {}
        for name in self.robot_names:
            self.clients[name] = ActionClient(self, NavigateToPose, f'/{name}/navigate_to_pose')

        # 任务队列（示例）
        self.task_queue = [
            {'robot': 'robot1', 'pose': [2.0, 1.5, 0.0]},
            {'robot': 'robot2', 'pose': [-1.0, -1.0, 0.0]},
        ]
        self.timer = self.create_timer(2.0, self.dispatch_tasks)

    def dispatch_tasks(self):
        if not self.task_queue:
            return
        task = self.task_queue.pop(0)
        robot = task['robot']
        pose = task['pose']

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = pose[0]
        goal_msg.pose.pose.position.y = pose[1]
        goal_msg.pose.pose.orientation.w = 1.0

        self.get_logger().info(f'Sending goal to {robot}: {pose}')
        if self.clients[robot].wait_for_server(timeout_sec=1.0):
            self.clients[robot].send_goal_async(goal_msg)
        else:
            self.get_logger().error(f'Action server for {robot} not available')

def main(args=None):
    rclpy.init(args=args)
    node = WMSDispatcher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()