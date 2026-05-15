# Headless Nav2 Ready-Gate Integration Validation

日期：`2026-05-15`

## 1. 结论

本轮已经完成 fresh session + headless 条件下的 Nav2 ready-gate 运行时集成测试，结论为：`Pass`。

本轮确认：

- `navigation.launch.py use_gz_gui:=false use_rviz:=false` 可正常启动
- `publish_initial_pose --preset start_zone` 后，系统进入完整 ready 状态
- `/map` 与 `/scan_filtered` 均可采样
- `map -> odom` TF 可用
- `/map_server`、`/amcl`、`/planner_server`、`/controller_server`、`/bt_navigator` 均为 `active [3]`
- `/navigate_to_pose` action server 数量为 `1`
- 整体 ready 证据在 `90s` 窗口内满足

本轮未发送 Nav2 goal。

## 2. 修改前判断

本轮主问题不是改导航参数或新增功能，而是把 `headless Nav2 ready-gate` 场景从规格文档推进到真实运行报告。

本轮文档改动文件：

- `docs/wms/reports/headless_nav2_ready_integration_validation_2026_05_15.md`
- `docs/acceptance_checklist.md`

本轮未修改：

- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- 地图、world、robot model

## 3. 测试范围

提交版本：

```text
f679732
```

本轮验证范围：

- headless `navigation.launch.py`
- `publish_initial_pose --preset start_zone`
- `/map`
- `/scan_filtered`
- `map -> odom`
- 5 个核心 lifecycle 节点
- `/navigate_to_pose` action server

本轮不在范围内：

- 不发送导航 goal
- 不执行 Mock WMS task runner
- 不执行 HTTP executor

## 4. 关键时间线

`T0` 来自 launch 日志：

```text
1778776118.6912684 [INFO] [launch]: All log files can be found below ...
```

按本地时区换算：

- `T0`：`2026-05-15 00:28:38.691` local
- first initial pose：`2026-05-15 00:29:13.698` local
- `Managed nodes are active`：`2026-05-15 00:29:17.338` local

由此可得：

- `time_to_initial_pose_publish`：约 `35.0s`
- `time_to_all_5_lifecycle_active`：约 `38.6s`
- `ready_within_90s`：`yes`

说明：

- `time_to_map_server_active` 和 `time_to_amcl_active` 本轮没有单独逐秒计时。
- 但从生命周期管理顺序可推断，它们都不晚于 `T+38.6s`；之后的显式 `ros2 lifecycle get` 采样也确认二者为 `active [3]`。

## 5. 执行命令摘要

```bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
```

```bash
python3 scripts/publish_initial_pose.py --preset start_zone --wait-for-subscribers 30
```

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
timeout 8s ros2 topic echo /map --once
timeout 8s ros2 topic echo /scan_filtered --once
timeout 4s ros2 run tf2_ros tf2_echo map odom
ros2 action info /navigate_to_pose
```

## 6. Ready Snapshot

显式 lifecycle 采样结果：

| 节点 | 结果 |
| --- | --- |
| `/map_server` | `active [3]` |
| `/amcl` | `active [3]` |
| `/planner_server` | `active [3]` |
| `/controller_server` | `active [3]` |
| `/bt_navigator` | `active [3]` |

topic / TF / action 采样结果：

| 检查项 | 实际结果 |
| --- | --- |
| `/map` | 成功返回 `frame_id: map`，并带有 map metadata |
| `/scan_filtered` | 成功返回 `frame_id: my_robot/lidar_link/lidar` 的 LaserScan 样本 |
| `map -> odom` | `tf2_echo` 成功返回有效平移与旋转矩阵 |
| `/navigate_to_pose` | `Action servers: 1`，server 为 `/bt_navigator` |

## 7. 关键运行证据

来自运行输出的关键证据包括：

- `Found 1 subscriber(s) on /initialpose.`
- `Published initial pose 10/10`
- `initialPoseReceived`
- `global_costmap.global_costmap: start`
- `Managed nodes are active`
- `active [3]` for all 5 lifecycle queries
- `/map` sample with `frame_id: map`
- `/scan_filtered` sample with LaserScan data
- `tf2_echo map odom` 返回有效变换
- `Action servers: 1`

## 8. 结果判定

| 验证项 | 预期 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| headless launch | 可正常启动 | 启动成功 | 通过 |
| initial pose | 能正常发布到 `/initialpose` | `10/10` published | 通过 |
| `/map` | 可采样 | 采样成功 | 通过 |
| `/scan_filtered` | 可采样 | 采样成功 | 通过 |
| `map -> odom` | `90s` 内可用 | 可用 | 通过 |
| 5 个 lifecycle nodes | `90s` 内全部 `active` | `T+38.6s` 前进入 ready，采样时均为 `active [3]` | 通过 |
| `/navigate_to_pose` | action server 数量为 `1` | `1` | 通过 |

## 9. 边界说明

- 在 initial pose 发布前，AMCL 和 global costmap 持续输出 “Please set the initial pose...” 与 `map` frame 相关 warning，这属于当前主线预期现象。
- 发布 initial pose 后，系统恢复并进入 ready-gate，通过标准满足。
- 本轮没有观察到需要手动重启节点或临时改参数的情况。
- 本轮验证的是“可进入 ready 状态”，不是“导航执行结果”。

## 10. 结论

本轮已经证明，当前主线在 fresh session + headless 条件下可以稳定进入后续导航执行所需的 ready 状态。

这意味着：

- 短距离 smoke 导航
- 固定任务点回归
- Mock WMS executor / HTTP executor

都具备当前主线要求的 ready-gate 前置基础。
