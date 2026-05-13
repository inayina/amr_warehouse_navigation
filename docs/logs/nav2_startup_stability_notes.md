# Nav2 Fresh Session Startup Stability Notes

日期：`2026-05-13`

本文件只基于 [docs/reports/repeat_navigation_test_report_2026_05_13.md](../reports/repeat_navigation_test_report_2026_05_13.md) 整理 fresh session 下的 Nav2 启动前置条件不稳定现象。

范围约束：

- 不讨论调参，不讨论地图、world、robot model 修改。
- 不修改 `navigation.launch.py`、`config/nav2_params.yaml`。
- 只整理已观测现象，不臆测根因。

## 1. 观察范围

- 观察来源：`RUN-01` 到 `RUN-12`
- 重点对象：fresh session 下 goal 发送前的前置条件
- 重点症状：
  - lifecycle 未完整 `5/5 active`
  - `/navigate_to_pose` 显示 `Action servers: 0`
  - `/bt_navigator` 查询返回 `Node not found`
  - 不同轮次在相近流程下状态不一致

## 2. 所有 `SKIPPED` 轮次摘录

| Run | 点位 | `map -> odom` | lifecycle 现象 | action 现象 | 结果 |
| --- | --- | --- | --- | --- | --- |
| `RUN-04` | `candidate_dock_a` | 可用 | `map_server`、`amcl` 为 `active [3]`，但 `planner_server`、`controller_server`、`bt_navigator` 为 `inactive [2]` | `/navigate_to_pose` server 为 `1` | `SKIPPED` |
| `RUN-07` | `staging_1` | 可用 | `ros2 node list` 可见整套 Nav2 节点；`/map_server`、`/controller_server`、`/bt_navigator` 为 `active [3]`，但 `/amcl`、`/planner_server` 返回 `Node not found` | `/navigate_to_pose` 为 `Action servers: 0` | `SKIPPED` |
| `RUN-08` | `inspection_point` | 可用 | `/map_server`、`/amcl`、`/planner_server`、`/controller_server` 为 `active [3]`，但 `/bt_navigator` 两次复核都返回 `Node not found` | `/navigate_to_pose` 为 `Action servers: 1` | `SKIPPED` |
| `RUN-09` | `station_b` | 可用 | `/map_server`、`/amcl`、`/planner_server`、`/controller_server` 为 `active [3]`，但 `/bt_navigator` 两次复核都返回 `Node not found` | `/navigate_to_pose` 两次复核都为 `Action servers: 0` | `SKIPPED` |
| `RUN-10` | `station_a` | 可用 | `ros2 node list` 可见 `/planner_server` 与 `/bt_navigator`，但对应 lifecycle 查询返回 `Node not found` | `/navigate_to_pose` 为 `Action servers: 0` | `SKIPPED` |
| `RUN-11` | `shelf_1` | 可用 | `/amcl`、`/planner_server`、`/controller_server`、`/bt_navigator` 为 `active [3]`，但 `/map_server` 返回 `Node not found` | `/navigate_to_pose` 为 `Action clients: 1`、`Action servers: 0` | `SKIPPED` |

补充参考：

- `RUN-01` 不是正式 `SKIPPED` 轮次，但它提供了一个重要前置现象：晚于启动时机补发 initial pose 后，`map -> odom` 可恢复，但 `planner_server`、`bt_navigator` 仍不会自动补齐到可发 goal 状态。

## 3. 按现象分类

### 3.1 lifecycle 未完整 `5/5 active`

报告中的直接表现：

- `RUN-04`：部分节点已 `active [3]`，但 `planner_server`、`controller_server`、`bt_navigator` 停在 `inactive [2]`
- `RUN-07`：部分节点 `active [3]`，但 `/amcl`、`/planner_server` 返回 `Node not found`
- `RUN-08`：除 `/bt_navigator` 外其余关键节点可查到 `active [3]`
- `RUN-09`：除 `/bt_navigator` 外其余关键节点可查到 `active [3]`
- `RUN-10`：`ros2 node list` 可见 `/planner_server`、`/bt_navigator`，但 lifecycle 查询返回 `Node not found`
- `RUN-11`：除 `/map_server` 外其余关键节点可查到 `active [3]`

仅从现象看，可以确认：

- fresh session 下，`5/5 active` 不是每轮都稳定满足
- “部分节点 active” 不等于“可安全发 goal”
- lifecycle 查询结果本身在不同轮次之间存在不一致

### 3.2 `/navigate_to_pose` 显示 `Action servers: 0`

报告中的直接表现：

- `RUN-01`：`/navigate_to_pose` server 为 `0`
- `RUN-07`：`Action servers: 0`
- `RUN-09`：两次复核都为 `Action servers: 0`
- `RUN-10`：`Action servers: 0`
- `RUN-11`：`Action clients: 1`，但 `Action servers: 0`
- `RUN-12`：首次检查为 `Action servers: 0`，短暂复核后恢复为 `1`

仅从现象看，可以确认：

- action server 是否可见，在 fresh session 下不是静态结果
- 即使 `map -> odom` 可用，甚至部分 lifecycle 已 `active [3]`，`/navigate_to_pose` 仍可能为 `0`
- `RUN-12` 说明 action server 结果可能随时间变化，单次检查不足以覆盖整轮状态

### 3.3 `/bt_navigator` 返回 `Node not found`

报告中的直接表现：

- `RUN-08`：`/bt_navigator` 两次复核都返回 `Node not found`，但 `/navigate_to_pose` 为 `Action servers: 1`
- `RUN-09`：`/bt_navigator` 两次复核都返回 `Node not found`
- `RUN-10`：`ros2 node list` 可见 `/bt_navigator`，但 lifecycle 查询返回 `Node not found`

仅从现象看，可以确认：

- `/bt_navigator` 的“节点存在性”在不同检查手段之间可能不一致
- `ros2 node list` 可见，并不等于 `ros2 lifecycle get /bt_navigator` 一定可用
- `action server` 可见，并不等于 `/bt_navigator` 的 lifecycle 查询一定可用

### 3.4 fresh session 间状态不一致

报告中的直接表现：

- `RUN-03` 与 `RUN-05`：都成功
- `RUN-04`：在相近启动流程下仍因 lifecycle 不完整而 `SKIPPED`
- `RUN-06`：成功
- `RUN-07`、`RUN-08`：独立 fresh session 下仍出现 lifecycle / action 侧不一致
- `RUN-09`、`RUN-10`、`RUN-11`：3 个业务点 fresh session 全部 `SKIPPED`
- `RUN-12`：同样是业务点 fresh session，但最终 `SUCCEEDED`

仅从现象看，可以确认：

- fresh session 启动状态在轮次之间有明显波动
- `map -> odom` 比 lifecycle / action 更稳定
- 同样的“先 launch，再发 initial pose，再检查”的大流程，无法保证每轮得到同样的 lifecycle / action 结果

## 4. 当前可以直接下的诊断结论

- 现有报告已经足够说明：当前 fresh session 的不稳定点主要在 Nav2 启动前置条件，而不是单个导航点本身。
- 在多轮 `SKIPPED` 中，最常见的阻塞不是 `TF`，而是 lifecycle 未完整、`/bt_navigator` 查询异常、`/navigate_to_pose` server 不可用。
- 同一轮中不同检查手段可能互相矛盾：
  - `ros2 node list` 可见节点
  - lifecycle 查询却返回 `Node not found`
  - action server 有时存在、有时为 `0`
- 因此，下一轮更适合做“启动稳定性诊断”，不适合直接把主要精力放在坐标或调参上。

## 5. 下一轮最小验证方案

目标：

- 不发 goal
- 不改参数
- 只复核 fresh session 下前置条件何时稳定、何时不一致

建议流程：

1. 每次只开一个 fresh session。
2. 启动后先记录 launch 起始时间。
3. 在发布 initial pose 前先做一轮检查。
4. 发布 `start_zone` initial pose 后，按固定时间点重复检查。
5. 在同一 session 内，至少保留 3 次重复采样，而不是只看单次结果。
6. 若出现 `ros2 node list`、lifecycle、action 三者不一致，只记录现象，不发 goal。

建议的最小时间点：

- `T+10s`：首次采样
- `T+15s`：第二次采样
- `T+20s`：发布 initial pose
- `T+25s`：第三次采样
- `T+30s`：第四次采样
- `T+35s`：第五次采样

每个时间点都记录以下对象：

- `ros2 node list`
- `ros2 lifecycle nodes`
- `ros2 lifecycle get /map_server`
- `ros2 lifecycle get /amcl`
- `ros2 lifecycle get /planner_server`
- `ros2 lifecycle get /controller_server`
- `ros2 lifecycle get /bt_navigator`
- `ros2 node info /bt_navigator`
- `ros2 action list`
- `ros2 action info /navigate_to_pose`
- `timeout 4s ros2 run tf2_ros tf2_echo map odom`

停止条件建议：

- 若 `5/5 lifecycle` 全部 `active [3]` 且 `/navigate_to_pose` 为 `Action servers: 1`，则本轮记为“前置条件稳定”
- 若到最后一个时间点仍未满足，则本轮记为“前置条件未稳定”

## 6. 建议检查命令

以下命令只用于诊断，不包含任何参数修改：

```bash
ros2 daemon stop
ps -ef | rg 'navigation.launch.py|gazebo|gz sim|amcl|planner_server|controller_server|bt_navigator'
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30
ros2 node list
ros2 lifecycle nodes
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
ros2 node info /bt_navigator
ros2 action list
ros2 action info /navigate_to_pose
timeout 4s ros2 run tf2_ros tf2_echo map odom
```

## 7. 记录重点

下一轮建议重点记录以下字段：

- fresh session 编号
- launch 开始绝对时间
- initial pose 发布时间
- 每次采样时间点
- `ros2 node list` 是否包含 `/bt_navigator`
- `ros2 lifecycle nodes` 是否列出 `/bt_navigator`
- `ros2 lifecycle get /bt_navigator` 是否返回 `active [3]`、`inactive [2]` 或 `Node not found`
- `/navigate_to_pose` 从 `Action servers: 0` 变为 `1` 的时间点
- `map -> odom` 是否已可用

这样做的价值是：

- 可以把“节点图可见”“lifecycle 可查”“action server 可用”这三类状态拆开观察
- 可以把“同一 session 内的时间变化”与“不同 session 间的波动”区分开
- 可以为下一步决定是否需要进一步排查 startup 链路提供更直接的证据
