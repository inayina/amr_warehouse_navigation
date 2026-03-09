FROM osrf/ros:jazzy-desktop-full

# 使用 root 权限安装
USER root

# 安装核心仿真、导航组件及常用开发工具
RUN apt-get update && apt-get install -y \
    python3-pip \
    ros-jazzy-ros-gz \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-ros-gz-bridge \
    nano \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# 自动加载 ROS 环境
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc

WORKDIR /ros2_ws