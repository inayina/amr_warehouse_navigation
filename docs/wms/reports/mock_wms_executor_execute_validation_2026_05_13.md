# Mock WMS Executor Execute Validation

日期：`2026-05-13`

## 1. 目标

本报告只记录 V3.1 `task_to_nav2_adapter / Mock WMS Task Executor` 的一次现场 execute-mode 验证。

本轮严格范围：

- 只验证 `station_a`
- 不修改 `navigation.launch.py`
- 不修改 `config/nav2_params.yaml`
- 不修改地图、world、robot model
- 不修改任何历史报告原始结果
- 不新增 HTTP / MQTT / Web 后台
- 不新增多机器人
- 不做自动循环派单
- 不直接发布 `/cmd_vel`
- 不调整 Nav2 参数

## 2. 现场前说明

本轮先发现了 3 个命令层面的实际不一致：

1. 当前 ROS 2 包名实际是 `amr_warehouse_sim`，不是 `amr_warehouse_navigation`
2. 当前仓库原本没有 `scripts/publish_initial_pose.py`
3. 当前 SQLite CLI 原本使用的是 `--db-path`，不是 `--db`

因此本轮只做了最小 CLI 兼容：

- 为 SQLite 相关脚本和 executor 增加 `--db` 兼容参数
- 为 executor 增加显式 `--dry-run` 兼容参数
- 新增 `scripts/publish_initial_pose.py` wrapper，对齐现场验证命令

说明：

- 包名不一致没有做重命名修复，本轮实际 launch 命令使用 `amr_warehouse_sim`
- 以上兼容不改变 executor 行为逻辑

## 3. 实际执行命令

### 3.1 Fresh session launch

实际执行：

```bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
```

补充说明：

- `ros2 launch amr_warehouse_navigation navigation.launch.py ...` 在当前环境中返回 `Package 'amr_warehouse_navigation' not found`
- 为避免沙箱导致的 Gazebo / DDS 受限，本轮现场验证命令在沙箱外执行

### 3.2 数据库初始化

由于 `data/mock_wms.db` 当时不存在，先最小初始化：

```bash
python3 scripts/init_mock_wms_db.py --db data/mock_wms.db
```

结果：

```text
[mock_wms_db] Initialized tasks table at: data/mock_wms.db
```

### 3.3 Initial pose

执行：

```bash
python3 scripts/publish_initial_pose.py --preset start_zone --wait-for-subscribers 30
```

结果：

- 找到 `1` 个 `/initialpose` subscriber
- 连续发布 `10/10` 条 `start_zone` 初始位姿

## 4. Validation Flow

### 4.1 Step C: executor dry-run precheck before task creation

执行：

```bash
python3 scripts/run_mock_wms_executor.py --db data/mock_wms.db --dry-run
```

结果：

```text
[mock_wms_executor] outcome=no-pending-task, mode=dry-run, task_id=n/a, target_name=n/a. No pending tasks found.
```

说明：

- 按当前实现，数据库中没有 `pending` task 时，dry-run 不会继续做 ready gate 检查

### 4.2 Step D: create one `station_a` pending task

执行：

```bash
python3 scripts/create_mock_task.py --db data/mock_wms.db --target station_a
```

结果：

```text
[mock_wms_db] Created pending task: id=1, task_name=mock-task-station_a-20260513T131125Z, target_name=station_a, frame_id=map, x=-5.3, y=-5.8, yaw=3.14, status=pending
```

### 4.3 Supplemental dry-run on the created `station_a` task

由于 Step C 在空库上只返回 `no-pending-task`，本轮补做了一次真正针对 `station_a` 的 dry-run，用来观察 execute 前的 gate 行为。

第一次补充 dry-run：

```text
[mock_wms_executor] outcome=ready-gate-not-ready, mode=dry-run, task_id=1, target_name=station_a. Nav2 ready gate not satisfied: /map_server lifecycle state is unavailable
```

同 session 补充采样：

- `ros2 lifecycle get /map_server` -> `Node not found`
- `ros2 lifecycle get /amcl` -> `Node not found`
- `ros2 lifecycle get /planner_server` -> `Node not found`
- `ros2 lifecycle get /controller_server` -> `Node not found`
- `ros2 lifecycle get /bt_navigator` -> `Node not found`
- `ros2 action info /navigate_to_pose` -> `Action servers: 0`
- `timeout 4s ros2 run tf2_ros tf2_echo map odom` -> `map -> odom` 可用

约 5 秒后再次 dry-run：

```text
[mock_wms_executor] outcome=dry-run-ready, mode=dry-run, task_id=1, target_name=station_a. Dry-run only: ready gate satisfied; NavigateToPose goal not sent.
```

这一点说明：

- 同一个 fresh session 内，ready gate 结果存在真实波动
- 本轮观察到的波动不是伪造失败，而是现场 discovery / readiness 不一致

### 4.4 Step E: real execute

执行：

```bash
python3 scripts/run_mock_wms_executor.py --db data/mock_wms.db --execute
```

结果：

```text
[mock_wms_executor] outcome=ready-gate-not-ready, mode=execute, task_id=1, target_name=station_a. Nav2 ready gate not satisfied: /map_server lifecycle state is unavailable
```

现场观察：

- executor 没有把任务推进到 `running`
- launch session 在 execute 时段沒有出现新的 goal 接收 / 导航执行日志
- 因此本轮沒有证据表明 `/navigate_to_pose` 实际收到了 `station_a` goal

### 4.5 Step F: list final task state

执行：

```bash
python3 scripts/list_mock_tasks.py --db data/mock_wms.db
```

结果：

```text
id  task_name                             target_name  x     y     yaw   status   status_reason                                                              created_at
--  ------------------------------------  -----------  ----  ----  ----  -------  -------------------------------------------------------------------------  --------------------
1   mock-task-station_a-20260513T131125Z  station_a    -5.3  -5.8  3.14  pending  Nav2 ready gate not satisfied: /map_server lifecycle state is unavailable  2026-05-13T13:11:25Z
```

直接查询 SQLite 结果：

```text
(1, 'mock-task-station_a-20260513T131125Z', 'station_a', 'pending', 'Nav2 ready gate not satisfied: /map_server lifecycle state is unavailable', '2026-05-13T13:11:25Z', '2026-05-13T13:13:25Z')
```

## 5. Result Summary

| Item | Observation |
| --- | --- |
| executor 是否通过 ready gate | `最终 execute 未通过`；同 session 中曾出现一次 supplemental dry-run `ready gate satisfied` |
| 是否进入 `running` | `否` |
| `/navigate_to_pose` 是否实际收到 goal | `否，未观察到 goal 发送后的 Nav2 接收证据` |
| action result | `无`；因为 execute 在 ready gate 被拦下，未进入 action 执行阶段 |
| SQLite 最终 task status | `pending` |
| `status_reason` | `Nav2 ready gate not satisfied: /map_server lifecycle state is unavailable` |
| 如果 skipped 或 failed，具体原因 | 当前实现不写 SQLite `skipped` 状态；本轮表现为 `pending + status_reason`，原因是 ready gate 波动导致 execute 时 `/map_server` lifecycle 查询不可用 |

## 6. 结论

本轮 V3.1 `station_a` execute-mode 现场验证沒有闭合到真正的 `/navigate_to_pose` action 执行。

准确结论应写为：

- fresh session 已成功启动
- `start_zone` initial pose 已成功发布
- `station_a` pending task 已成功写入 SQLite
- executor 在同一 session 内出现过一次 `dry-run-ready`
- 但真正 `--execute` 那次又落回 `ready-gate-not-ready`
- 任务未进入 `running`
- SQLite 最终保持 `pending`
- `status_reason` 已准确记录失败原因

因此，到 `2026-05-13` 本轮收工时，V3.1 executor 的离线状态机与 dry-run contract 已通过，但 `station_a` 的 execute-mode 现场验证只能如实记为：

```text
Nav2 startup / discovery readiness fluctuated within the same fresh session,
so the executor did not reliably cross the ready gate at execute time.
```

## 7. Follow-Up Change

基于这次现场结果，当前主线继续推进的最小动作不是修改 Nav2 参数或 launch，而是增强 executor 自身的 execute 前 ready gate 等待能力。

本轮新增原因明确如下：

- 同一个 fresh session 内，已经观察到 `dry-run-ready`
- 但几秒后真正 `--execute` 又回到 `ready-gate-not-ready`
- 这说明 execute 失败点至少有一部分来自 ready 状态波动，而不是固定点坐标、地图或 Nav2 参数本身

因此，executor 本轮后续最小改动方向是：

- 只在 `--execute` 前增加 ready gate wait / retry
- 在 timeout 窗口内重复检查当前已有 gate
- 只有 gate 真正全部满足时才允许发 `/navigate_to_pose`
- timeout 内始终不 ready 时，保持 task 为 `pending` 并写入最后一次失败原因

本轮仍然沒有做以下变更：

- 没有修改 `navigation.launch.py`
- 没有修改 `config/nav2_params.yaml`
- 没有修改地图、world、robot model
- 没有伪造 action result
- 没有在 ready gate 不满足时强行发 goal

