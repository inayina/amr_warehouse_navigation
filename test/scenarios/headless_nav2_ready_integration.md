# Scenario: Headless Nav2 Ready-Gate Integration

这个场景用于验证当前主线在 **fresh session + headless** 条件下，是否能稳定进入可执行导航的 ready 状态。

它属于当前主线的关键运行时验证场景，因为后续无论是短距离 goal、固定任务点回归，还是 Mock WMS executor over HTTP，都依赖这条 ready-gate 前置链路。

## 场景目标

- 验证 `navigation.launch.py` 在 `use_gz_gui:=false use_rviz:=false` 下能正常启动
- 验证 `publish_initial_pose --preset start_zone` 后，系统是否能进入完整 ready gate
- 验证 `/map`、`/scan_filtered`、`map -> odom`、lifecycle nodes、`/navigate_to_pose` action server 是否在可接受时间窗口内就绪

## 适用范围

- 当前主线：AMR 仓储导航 + 最小 Mock WMS 任务执行闭环
- 主入口：`launch/navigation.launch.py`
- 参数文件：`config/nav2_params.yaml`
- 地图入口：`maps/warehouse.yaml`
- initial pose 工具：`ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`

## 不在本场景内

- 不发送 Nav2 goal
- 不执行 Mock WMS task runner 或 HTTP executor
- 不修改 `navigation.launch.py`、`config/nav2_params.yaml`、地图、world 或 robot model

## 前置条件

- 已完成编译并 `source install/setup.bash`
- 当前工作区没有残留的 Gazebo / Nav2 / bridge / RViz 会话
- 当前测试轮次不临时改参数
- 建议先准备一个单独日志文件，例如：
  `/tmp/headless_nav2_ready_integration.log`

## 执行步骤

1. 清理遗留进程，确保使用 fresh session。
2. 启动 headless navigation：
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
3. 记录启动时间 `T0`。
4. 在 `T+10s` 左右发布 initial pose：
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
5. 每隔 `10~20s` 采样一次下面的状态，直到全部 ready 或超时：
   `ros2 lifecycle get /map_server`
   `ros2 lifecycle get /amcl`
   `ros2 lifecycle get /planner_server`
   `ros2 lifecycle get /controller_server`
   `ros2 lifecycle get /bt_navigator`
   `ros2 topic echo /map --once`
   `ros2 topic echo /scan_filtered --once`
   `timeout 4s ros2 run tf2_ros tf2_echo map odom`
   `ros2 action info /navigate_to_pose`
6. 如果所有前置条件都满足，记录 `T_ready` 并结束本轮。
7. 如果达到超时时间仍未 ready，记录最后一次快照和失败原因。

## 建议记录的指标

- `time_to_map_server_active`
- `time_to_amcl_active`
- `time_to_all_5_lifecycle_active`
- `time_to_map_odom_available`
- `time_to_navigate_to_pose_available`
- `ready_within_90s`
- `notes`

## 通过标准

- `/map` 和 `/scan_filtered` 均可正常采样
- `map -> odom` 在 `90s` 内可用
- `/map_server`、`/amcl`、`/planner_server`、`/controller_server`、`/bt_navigator` 在 `90s` 内全部为 `active`
- `/navigate_to_pose` action server 数量为 `1`
- 过程中不需要手动重启节点，不需要临时改参数

## 失败分级建议

- `Blocker`
  `navigation.launch.py` 无法正常启动，或 `/map`、`/scan_filtered`、`map -> odom` 主链断裂
- `Major`
  localization 可以建立，但 5 个 lifecycle nodes 长时间无法全部进入 `active`
- `Minor`
  最终能 ready，但等待时间明显偏长，或需要多次补发 initial pose

## 建议保留的证据

- lifecycle 状态输出
- `ros2 topic echo /map --once`
- `ros2 topic echo /scan_filtered --once`
- `timeout 4s ros2 run tf2_ros tf2_echo map odom`
- `ros2 action info /navigate_to_pose`
- launch 日志

## 结果记录模板

| Run ID | Time to `/map_server active` | Time to `all 5 active` | Time to `map -> odom` | Time to action ready | Ready Within 90s | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 001 |  |  |  |  |  |  |

## 常见失败归因方向

- `/map_server` 或 `/amcl` 长时间不可用
  优先检查 initial pose 时机、map_server / localization bringup 和 ROS discovery
- `map -> odom` 不可用
  优先检查 initial pose、AMCL、`/scan_filtered` 和 TF 连通性
- action server 数量为 `0`
  优先检查 `bt_navigator`、lifecycle 状态和 bringup 完整性
- headless 比 GUI 更不稳定
  优先检查 fresh session 清理是否彻底、日志中是否存在时序或 discovery 波动
