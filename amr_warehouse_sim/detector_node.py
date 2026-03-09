import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np

class RedObstacleDetector(Node):
    def __init__(self):
        super().__init__('detector_node')
        # 1. 订阅 Gazebo 摄像头发出的原始图像 (已强制对齐带有模型前缀的完整路径)
        self.subscription = self.create_subscription(
            Image, 
            '/model/my_robot/camera/image_raw', 
            self.image_callback, 
            10)
        
        # 2. 发布处理后的状态给 Agent 节点
        self.status_pub = self.create_publisher(String, '/obstacle_status', 10)
        
        self.bridge = CvBridge()
        self.last_status = "CLEAR"
        self.first_frame = True # 用于控制日志，只在收到第一张图时通报一次
        
        self.get_logger().info('感知节点已就绪：正在监控 /model/my_robot/camera/image_raw ...')

    def image_callback(self, msg):
        # 只要这行绿色的字打出来，说明物理层和应用层彻底通了！
        if self.first_frame:
            self.get_logger().info('✅ 成功接收到第一帧图像，视觉链路已打通！')
            self.first_frame = False

        # 安全的图像转换逻辑：使用 try-except 防止编码异常引发节点静默崩溃
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f'CvBridge 转换失败: {e}')
            return
        
        # 转换到 HSV 空间进行颜色识别
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 定义红色范围（Jazzy/Harmonic 环境下的标准红）
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([179, 255, 255])

        # 合并双区间 Mask
        mask = cv2.addWeighted(cv2.inRange(hsv, lower_red1, upper_red1), 1.0, 
                                cv2.inRange(hsv, lower_red2, upper_red2), 1.0, 0)

        # 形态学去噪，让识别更稳定
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        
        # 寻找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        current_status = "CLEAR"
        max_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500: # 过滤杂色小点
                if area > max_area:
                    max_area = area
                x, y, w, h = cv2.boundingRect(cnt)
                # 画出绿色识别框
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # 核心决策逻辑：根据最大的红色色块面积判断距离
        if max_area > 12000:   # 离得非常近
            current_status = "STOP"
        elif max_area > 3000:  # 看到障碍物
            current_status = "WARNING"

        # 只有状态改变时才打印日志，保持终端清爽
        if current_status != self.last_status:
            self.get_logger().info(f'状态切换: {self.last_status} -> {current_status} (面积: {int(max_area)})')
            self.last_status = current_status

        # 每帧都发布状态消息，确保 Agent 大脑始终掌握最新鲜的信号
        status_msg = String()
        status_msg.data = current_status
        self.status_pub.publish(status_msg)

        # 在窗口上实时绘制当前状态文字
        color = (0, 255, 0) if current_status == "CLEAR" else (0, 0, 255)
        cv2.putText(frame, f"Status: {current_status}", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        # 显示 OpenCV 调试窗口（宿主机环境可直接开启）
        cv2.imshow("AMR Camera View", frame)
        cv2.waitKey(1)

# --- 顶层 main 函数 ---
def main(args=None):
    rclpy.init(args=args)
    node = RedObstacleDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("\n正在关闭感知节点...")
    finally:
        # 必须销毁窗口和节点，防止残留进程卡死桌面
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()