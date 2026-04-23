# 🔍 常见问题排查

### 1. 窗口未弹出
- 检查宿主机是否执行了 `xhost +local:docker`
- 检查 `DISPLAY` 环境变量是否正确

### 2. 导航不移动
- 检查 `ros2 topic echo /cmd_vel` 是否有输出
- 检查雷达数据是否通过 bridge 正确传输
