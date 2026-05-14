# Nav2 启动稳定性诊断日志

日期：`2026-05-13`

来源说明：本轮诊断沿用 [nav2_startup_stability_notes.md](./nav2_startup_stability_notes.md) 中的诊断方向，并根据现场观察做了一处修正：仅发布 `start_zone` initial pose 还不足以实际触发导航链路，因此每一轮计入结果的测试都会额外发送一个指向 `candidate_dock_a` 的诊断 goal probe。

范围：

- 本轮未修改 `navigation.launch.py`。
- 本轮未修改 `config/nav2_params.yaml`。
- 本轮未修改地图、world、机器人模型或 `config/task_points.yaml`。
- 诊断 goal 不计入导航点位复测结果；它只用于观察启动链路是否已经 ready，能否接受并执行 Nav2 action。

## 验证流程

每一轮计入结果的测试都使用 fresh session：

1. 停止 ROS daemon，并清理遗留的 Nav2 / Gazebo / bridge / robot state / odom TF 进程。
2. 启动：
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
3. 在约 `T+10s` 和 `T+20s` 记录状态。
4. 发布 initial pose：
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
5. 在约 `T+30s` 记录状态。
6. 向 `candidate_dock_a` 发送一次诊断 goal probe：
   `map: x=0.0, y=-3.8, yaw=-1.57`
7. 在约 `T+45s` 和 `T+60s` 记录状态。

本日志中的 READY 定义：

- `/map_server`、`/amcl`、`/planner_server`、`/controller_server`、`/bt_navigator` 全部为 `active [3]`
- `/navigate_to_pose` 显示 `Action servers: 1`
- 短时间 `tf2_echo` 中可以观察到 `map -> odom`

Goal 结果与 READY / NOT_READY 判定分开记录。

## 丢弃的尝试

- 修正流程前曾执行过一次只发布 initial pose 的诊断。由于没有发送 goal probe，该轮不计入结果。
- 另有一次 goal probe 尝试被丢弃，因为预清理检查发现上一轮遗留的 launch / Gazebo / Nav2 进程。该轮不是有效 fresh session。

## 轮次时间线

### GOAL-PROBE-01

开始时间：`2026-05-13T14:57:35+08:00`

| 时间 | 关键节点存在性 | Lifecycle 状态 | Action server | TF `map -> odom` | 备注 |
| --- | --- | --- | --- | --- | --- |
| `T+10s` | `ros2 node list` 中尚未看到关键 Nav2 节点 | 查询到的关键节点全部返回 `Node not found` | `0` | `no` | 启动仍未完成 |
| `T+20s` | 关键节点可见 | `/map_server active [3]`、`/amcl active [3]`、`/controller_server active [3]`、`/planner_server inactive [2]`、`/bt_navigator inactive [2]` | `1` | `no` | action server 已出现，但导航 lifecycle 仍未完整 ready |
| initial pose | `/initialpose` 有 `1` 个 subscriber | 已发布 `10/10` 条消息 | N/A | N/A | `start_zone` 发布成功 |
| `T+30s` | 关键节点可见 | 与 `T+20s` 相同；`/planner_server` 和 `/bt_navigator` 仍为 `inactive [2]` | `1` | `yes` | initial pose 恢复了 TF，但没有完成 lifecycle |
| goal probe | N/A | 发送前 lifecycle 仍不完整 | action server 可用 | TF 可用 | goal 被拒绝 |
| `T+45s` | 关键节点可见 | `/planner_server inactive [2]`、`/bt_navigator inactive [2]` | `1` | `yes` | goal 后未观察到 lifecycle 恢复 |
| `T+60s` | 关键节点可见 | `/planner_server inactive [2]`、`/bt_navigator inactive [2]` | `1` | `yes` | 仍未 ready |

最终判定：`NOT_READY`

观察到的 goal 结果：`REJECTED`

### GOAL-PROBE-02

开始时间：`2026-05-13T15:04:05+08:00`

| 时间 | 关键节点存在性 | Lifecycle 状态 | Action server | TF `map -> odom` | 备注 |
| --- | --- | --- | --- | --- | --- |
| `T+10s` | 部分节点可见 | lifecycle discovery 不完整；`/bt_navigator` 返回 `unconfigured [1]` | `0` | `no` | 启动仍在进行 |
| `T+20s` | 关键节点可见 | `/map_server active [3]`、`/amcl active [3]`、`/controller_server active [3]`、`/bt_navigator inactive [2]`；捕获行中 `/planner_server` 查询未返回稳定状态 | `1` | `no` | action server 早于完整 ready 状态出现 |
| initial pose | `/initialpose` 有 `1` 个 subscriber | 已发布 `10/10` 条消息 | N/A | N/A | `start_zone` 发布成功 |
| `T+30s` | 关键节点可见 | 5 个关键 lifecycle nodes 全部为 `active [3]` | `1` | `yes` | 发送诊断 goal 前已经达到 READY |
| goal probe | N/A | 发送前 5 个关键 lifecycle nodes 全部 active | action server 可用 | TF 可用 | goal 被接受 |
| `T+45s` | 关键节点可见 | 5 个关键 lifecycle nodes 全部为 `active [3]` | `1` | `yes` | goal 执行后 ready 状态保持 |
| `T+60s` | 关键节点可见 | 5 个关键 lifecycle nodes 全部为 `active [3]` | `1` | `yes` | 仍然 ready |

最终判定：`READY`

观察到的 goal 结果：`SUCCEEDED`

### GOAL-PROBE-03

开始时间：`2026-05-13T15:12:58+08:00`

| 时间 | 关键节点存在性 | Lifecycle 状态 | Action server | TF `map -> odom` | 备注 |
| --- | --- | --- | --- | --- | --- |
| `T+10s` | 部分节点可见 | `/map_server active [3]`、`/amcl active [3]`、`/controller_server active [3]`、`/bt_navigator inactive [2]`；部分 node-list 检查仍不完整 | `1` | `no` | action server 较早可见，但 TF 尚未 ready |
| `T+20s` | 关键节点可见 | `/amcl active [3]`、`/controller_server active [3]`、`/bt_navigator inactive [2]`；部分 lifecycle 行在命令 timeout 下捕获为空 | `1` | `no` | initial pose 前仍未 ready |
| initial pose | `/initialpose` 有 `1` 个 subscriber | 已发布 `10/10` 条消息 | N/A | N/A | `start_zone` 发布成功 |
| `T+30s` | 关键节点可见 | 5 个关键 lifecycle nodes 全部为 `active [3]` | `1` | `yes` | 发送诊断 goal 前已经达到 READY |
| goal probe | N/A | 发送前 5 个关键 lifecycle nodes 全部 active | action server 可用 | TF 可用 | goal 被接受 |
| `T+45s` | 关键节点可见 | 5 个关键 lifecycle nodes 全部为 `active [3]` | `1` | 短检查中为 `no` | lifecycle 和 action 保持 ready；但本次短 TF 检查没有观察到 `map -> odom` |
| `T+60s` | 关键节点可见 | 5 个关键 lifecycle nodes 全部为 `active [3]` | `1` | `yes` | 再次观察到 TF |

最终判定：`READY`

观察到的 goal 结果：`ABORTED`

## 汇总

| 指标 | 数量 | 比例 |
| --- | --- | --- |
| 计入结果的 fresh sessions | `3` | `100%` |
| READY | `2` | `66.7%` |
| NOT_READY | `1` | `33.3%` |
| Goal accepted | `2` | `66.7%` |
| Goal rejected | `1` | `33.3%` |
| Goal succeeded | `1` | `33.3%` |
| Goal aborted | `1` | `33.3%` |

## 观察到的模式

- 在 NOT_READY 轮次中，发布 initial pose 恢复了 `map -> odom`，但没有让 `/planner_server` 或 `/bt_navigator` 从 `inactive [2]` 进入 `active [3]`。
- `/navigate_to_pose` 可能在完整 lifecycle 前置条件满足之前就显示 `Action servers: 1`。
- 在两轮 READY 结果中，系统都在 initial pose 后第一次采样附近，也就是约 `T+30s` 时达到 ready，早于诊断 goal 发送。
- 发送诊断 goal 没有把 NOT_READY 轮次转为 READY。在 GOAL-PROBE-01 中，goal 被拒绝，lifecycle 仍保持不完整。
- Goal 结果和启动 ready 状态相关，但并不完全等价。GOAL-PROBE-03 达到了 READY、接受了 goal，但最终 goal 结果是 `ABORTED`。

## 诊断结论

三轮计入结果的 fresh sessions 表明，在修正后的流程下仍存在启动 ready 状态不稳定：

- `2/3` 轮在观测窗口内达到了完整前置条件集合。
- `1/3` 轮即使发布 initial pose 并尝试诊断 goal 后，仍未达到完整 lifecycle ready。
- 最清晰、反复出现的不稳定点仍然是 lifecycle convergence，尤其是 NOT_READY 轮次中 `/planner_server` 和 `/bt_navigator` 保持 `inactive [2]`。

本日志不对根因做归因。
