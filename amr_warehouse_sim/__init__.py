import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image       # 处理图像
from std_msgs.msg import String         # 处理字符串状态
from cv_bridge import CvBridge          # 桥接 OpenCV
import cv2                              # OpenCV 核心库
import numpy as np  
def __init__(self):
        # 1. 调用父类初始化，设置节点名称
        super().__init__('detector_node')

        # 2. 定义订阅者：订阅 Gazebo 发布的原始图像话题
        # 注意：这里的话题名必须和你抓到的 '/camera/image_raw' 完全一致
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.listener_callback,
            10)

        # 3. 定义发布者：向 Agent 发送识别结果 (CLEAR/WARNING/STOP)
        self.status_pub = self.create_publisher(
            String,
            '/obstacle_status',
            10)

        # 4. 初始化 CvBridge：这是 ROS 图像消息转为 OpenCV 矩阵的桥梁
        self.bridge = CvBridge()

        # 5. 定义颜色识别的面积阈值（可以根据箱子大小微调）
        # 如果箱子在画面中占据的像素超过这个值，就判定为 WARNING
        self.obstacle_area_threshold = 2000 

        self.get_logger().info('--- 视觉感知节点已激活 ---')
        self.get_logger().info('正在监听话题: /camera/image_raw')
        self.get_logger().info('正在发布话题: /obstacle_status')                   # 矩阵运算