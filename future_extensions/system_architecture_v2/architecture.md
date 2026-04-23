# 🏗️ 系统架构说明

## 数据流向
1. **感知层**: Gazebo (Lidar/Odom) -> ros_gz_bridge -> ROS 2 Topics
2. **决策层**: Nav2 (全局/局部规划) -> cmd_vel -> 机器人运动
3. **监控层**: AI Diagnostic Agent 监听 /odom 和 /scan 判定健康状态
4. **业务层**: WMS Dispatcher 发布 /goal_pose 驱动机器人任务

## 节点图谱
- /gz_sim: 物理引擎
- /controller_server: 局部运动控制
- /planner_server: 路径搜索
- /ai_diagnostic_agent: 自定义 AI 诊断
