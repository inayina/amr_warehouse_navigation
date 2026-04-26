# Scenario: Short-Range Navigation Smoke Test

这个场景用于验证当前 V2 稳定基线是否还能完成一次短距离、低风险、可重复的导航任务。

它很适合作为你投新兴机器人公司时展示的第一类场景测试，因为它能体现：

- 你会把系统验证拆成可执行场景
- 你会定义通过标准，而不是只说“我试过能跑”
- 你会留证据、记录结果、做失败归因

## 场景目标

- 验证 `navigation.launch.py` 启动后的最小导航闭环是否成立
- 验证机器人是否能在当前仓库环境下完成一次 1 到 2 米的短距离 goal
- 验证 `/cmd_vel`、TF、localization 和 planner / controller 之间的主链是否工作

## 适用范围

- 当前主线：V2 Nav2 导航与路径执行
- 主入口：`launch/navigation.launch.py`
- 参数文件：`config/nav2_params.yaml`
- 地图入口：`maps/warehouse.yaml`

## 前置条件

- 已完成编译并 `source install/setup.bash`
- `ros2 launch amr_warehouse_sim navigation.launch.py` 可以正常启动
- `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 进入 `active`
- RViz 中已设置 initial pose
- 目标点位于同一条可通行货架通道内，不穿越货架或墙体

## 执行步骤

1. 启动：
   `./scripts/run_navigation.sh`
   或
   `ros2 launch amr_warehouse_sim navigation.launch.py`
2. 确认 lifecycle nodes 已进入 `active`
3. 确认 `/map` 正常发布，`/scan_filtered` 正常发布，`map -> odom -> base_link` 连通
4. 在 RViz 中设置 initial pose
5. 在机器人当前所在通道内选择一个 1 到 2 米的短距离 goal
6. 发送 goal 后开始计时
7. 观察机器人是否输出 `/cmd_vel` 并开始移动
8. 观察是否成功到达目标点，或出现 oscillation、recovery、`Failed to make progress`
9. 保存结果和证据

## 建议记录的指标

- `time_to_first_cmd_vel`
  发送 goal 到首次出现 `/cmd_vel` 的时间
- `goal_completion_time`
  发送 goal 到导航完成的总时间
- `recovery_count`
  执行过程中 recovery 的触发次数
- `goal_result`
  `success` / `failed` / `aborted`
- `notes`
  记录贴墙、切角、抖动、定位漂移等现象

## 通过标准

- 发送 goal 后 3 秒内出现 `/cmd_vel`
- 机器人能在 30 秒内完成短距离导航
- `map -> odom -> base_link` 在测试期间持续连通
- 不出现明显撞墙、穿货架、长时间原地振荡
- `Failed to make progress` 不是本次测试的主导失败现象

## 失败分级建议

- `Blocker`
  goal 发出后机器人完全不动，或 TF / localization 主链断裂
- `Major`
  机器人移动但无法到达目标，或持续 oscillation / recovery
- `Minor`
  能到达目标，但路径明显切角、贴货架、耗时异常

## 建议保留的证据

- RViz 截图
- lifecycle 状态输出
- `ros2 topic echo /map --once`
- `ros2 topic echo /scan_filtered --once`
- `ros2 run tf2_ros tf2_echo map odom`
- 可选：屏幕录制、`rosbag`、`/cmd_vel` 采样日志

## 结果记录模板

| Run ID | Goal Description | Time to First `/cmd_vel` | Completion Time | Recovery Count | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 001 | 例：同通道前方短距离点 |  |  |  |  |  |

## 常见失败归因方向

- 没有 `/cmd_vel`
  优先检查 initial pose、`map -> odom`、lifecycle 状态
- 有 `/cmd_vel` 但机器人不动
  优先检查 Gazebo 运动链和 bridge
- 频繁 recovery
  优先检查 footprint、inflation、progress checker 和局部障碍层
- 能动但明显贴墙或切角
  优先检查 costmap、footprint 和全局 / 局部控制参数
