import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String

class WarehouseAgent(Node):
    def __init__(self):
        super().__init__('agent_node')
        self.cmd_pub = self.create_publisher(Twist, '/model/my_robot/cmd_vel', 10)
        self.detect_sub = self.create_subscription(String, '/obstacle_status', self.decision_callback, 10)
        self.timer = self.create_timer(0.1, self.main_loop)
        
        self.status = "CLEAR"
        self.last_status = "CLEAR"
        self.recovery_ticks = 0
        
        # 【核心优化点1】平滑度参数
        self.target_linear = 0.0
        self.target_angular = 0.0
        self.current_linear = 0.0
        self.current_angular = 0.0

        self.get_logger().info('🤖 稳定增强版 Agent 已启动，准备录制 GitHub Demo...')

    def decision_callback(self, msg):
        self.status = msg.data

    def main_loop(self):
        # 1. 状态决策
        if self.status == "WARNING":
            # 减小转向力度（0.6 -> 0.4），防止翻车
            self.target_linear = 0.12
            self.target_angular = 0.4 
            self.recovery_ticks = 12 # 略微缩短回正时间
        elif self.status == "STOP":
            self.target_linear = -0.05 # 极慢速后退，保命要紧
            self.target_angular = 0.5
        elif self.status == "CLEAR":
            if self.recovery_ticks > 0:
                self.target_linear = 0.15
                self.target_angular = -0.25 # 减小回正力度，防止反向翻车
                self.recovery_ticks -= 1
            else:
                self.target_linear = 0.2
                self.target_angular = 0.0

        # 【核心优化点2】线性插值平滑控制（防止电机突变导致翻车）
        # 每次循环只让速度变化 0.05，这样小车动作会变得“肉”一点，但很稳
        self.current_linear += (self.target_linear - self.current_linear) * 0.3
        self.current_angular += (self.target_angular - self.current_angular) * 0.3

        move_cmd = Twist()
        move_cmd.linear.x = self.current_linear
        move_cmd.angular.z = self.current_angular
        self.cmd_pub.publish(move_cmd)

def main(args=None):
    rclpy.init(args=args)
    node = WarehouseAgent()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_pub.publish(Twist()) # 停止
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()