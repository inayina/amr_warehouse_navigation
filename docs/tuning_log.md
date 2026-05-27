# Tuning Log

日期：`2026-05-27`

## 1. Purpose

本文件记录 AMR 仿真导航主线中 footprint、inflation、progress checker、controller 等参数的调试经验。当前内容是经验整理，不代表本轮修改了 `config/nav2_params.yaml`。

## 2. Baseline Principle

当前稳定基线是：

- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- `maps/warehouse.yaml`
- `config/task_points.yaml`

调参原则：

- 一次只改一类问题，例如 footprint、inflation 或 controller，不混合改动。
- 每次调参后至少做短距离 goal、固定任务点 goal、lifecycle / action readiness 检查。
- 真实结果要写入日期化报告，不直接覆盖历史结论。
- 任务层问题不要反向归因到 Nav2 参数，除非 ready gate 和 action 状态已经确认正常。

## 3. Footprint

经验判断：

- footprint 过大时，global / local costmap 会更保守，窄通道中可能出现绕行、无法规划或贴近障碍时停止。
- footprint 过小时，RViz 中路径看起来更容易通过，但仿真机器人可能出现贴墙、贴货架或碰撞风险。
- footprint 与 robot model 的外形、雷达安装位置、local costmap inflation 需要一起观察，但不应一次性同时大改。

建议验证：

- RViz 中打开 RobotModel、TF、local costmap、global costmap。
- 在 `station_a`、`station_b`、`shelf_1`、`shelf_2` 做固定点位复跑。
- 观察路径是否明显穿货架、贴墙或在拐角处振荡。

## 4. Inflation

经验判断：

- inflation radius 过大时，窄通道成本区域会压缩可通行空间，planner 更容易找不到路径或走大绕行。
- inflation radius 过小时，路径可能更贴近障碍，controller 容错空间变小。
- cost scaling 调得过陡时，路径可能突然贴边；调得过平时，机器人可能过度保守。

建议验证：

- 同屏观察 global path、local path 和 inflation layer。
- 优先在已有地图与固定任务点上复测，不同时修改地图。
- 对比 “能规划” 和 “能稳定执行完成”，不要只看规划成功。

## 5. Progress Checker

经验判断：

- progress checker 过严时，机器人在起步、转向、避障或狭窄区域容易触发 `Failed to make progress`。
- progress checker 过松时，真实卡住或长时间原地调整不容易被及时识别。
- fresh session 中若 lifecycle 或 `/navigate_to_pose` action server 不稳定，不应先归因到 progress checker。

建议验证：

- 记录 goal 开始时间、首次 `/cmd_vel` 输出时间、是否触发 recovery。
- 区分 “没有 ready” 和 “ready 后执行失败”。
- 对 `ABORTED`、`SKIPPED`、`SUCCEEDED` 分开记录。

## 6. Controller

经验判断：

- controller 参数影响局部跟踪、转向、贴边、振荡和最终到点姿态。
- 最大速度、加速度、角速度过激时，仿真中可能出现局部路径跟踪过冲。
- 过保守时，任务执行时间变长，progress checker 更容易成为限制项。

建议验证：

- 看 `/cmd_vel` 是否持续输出且方向合理。
- 观察机器人是否在目标点附近反复旋转、前后抖动或无法满足 yaw。
- 对短距离 goal 和跨通道 goal 分开记录，不把两类结果混成一个结论。

## 7. Startup Readiness

已观测经验：

- fresh session 下，`map -> odom` 可用不等于完整 Nav2 ready。
- lifecycle 查询、`ros2 node list` 和 `/navigate_to_pose` action server 可能短时间内不一致。
- initial pose 应在启动早期显式发布，当前推荐使用 `--wait-for-subscribers 30`。

推荐 ready gate：

```text
map_server active
amcl active
planner_server active
controller_server active
bt_navigator active
/navigate_to_pose action server available
map -> odom transform available
```

详细现象见：

- [logs/nav2_startup_stability_notes.md](./logs/nav2_startup_stability_notes.md)
- [wms/reports/headless_nav2_ready_integration_validation_2026_05_15.md](./wms/reports/headless_nav2_ready_integration_validation_2026_05_15.md)

## 8. Suggested Record Template

| 日期 | 改动文件 | 参数类型 | 验证点位 | 结果 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `YYYY-MM-DD` | `config/nav2_params.yaml` | footprint / inflation / progress / controller | `station_a` | `SUCCEEDED / ABORTED / SKIPPED` | 记录 ready gate、路径、costmap 和 `/cmd_vel` 现象 |

当前建议：除非正在处理明确导航问题，否则保持 `config/nav2_params.yaml` 稳定基线不动。
