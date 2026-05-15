# Mock WMS Not-Ready Guard Runtime Validation

日期：`2026-05-15`

## 1. 结论

本轮已经完成当前主线一次“Nav2 not ready 时不发 goal”的真实运行时负例验证，结论为：`Pass`。

本轮确认：

- fresh headless Nav2 会话在未注入 initial pose 时，不满足 ready gate
- `mock_wms_executor --execute` 不会冒进发送 `NavigateToPose` goal
- SQLite 任务不会被错误消费
- 任务会保留为 `pending`，并写入可追溯的 `status_reason`

## 2. 修改前判断

本轮主问题不是新增保护逻辑，而是把已经存在于 contract test 中的 ready-gate 语义补成一份正式的运行时负例报告，便于系统集成、验收和面试场景复核。

本轮文档改动文件：

- `docs/wms/reports/mock_wms_not_ready_guard_runtime_validation_2026_05_15.md`
- `docs/acceptance_checklist.md`

本轮未修改：

- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- 地图、world、robot model
- Mock WMS executor / task runner 代码逻辑

## 3. 范围与方法

提交版本：

```text
f679732
```

本轮验证方法：

1. 启动 fresh headless Nav2 会话：
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
2. 不发布 initial pose，保留系统处于 not-ready 状态
3. 创建单条 `station_a` pending task
4. 执行：
   `ros2 run amr_warehouse_sim mock_wms_executor --db ... --execute --ready-timeout 20 --ready-poll-interval 2 --navigation-timeout 120`
5. 检查 executor 输出、launch 输出和 SQLite 最终状态

本轮运行资源：

- 临时 DB：`/tmp/mock_wms_not_ready_guard_2026_05_15.db`
- headless launch 日志目录：
  `/tmp/mock_wms_executor_validation_ros_logs/2026-05-15-00-36-00-705020-ina-Gen6-531911`

说明：

- 报告日期使用本地日期 `2026-05-15`。
- SQLite `created_at` / `updated_at` 为 UTC 时间。

## 4. 执行命令摘要

```bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
```

```bash
ros2 run amr_warehouse_sim init_mock_wms_db --db /tmp/mock_wms_not_ready_guard_2026_05_15.db
ros2 run amr_warehouse_sim create_mock_task \
  --db /tmp/mock_wms_not_ready_guard_2026_05_15.db \
  --target station_a \
  --task-name not-ready-station-a-run-01
```

```bash
ros2 run amr_warehouse_sim mock_wms_executor \
  --db /tmp/mock_wms_not_ready_guard_2026_05_15.db \
  --execute \
  --ready-timeout 20 \
  --ready-poll-interval 2 \
  --navigation-timeout 120
```

```bash
sqlite3 -header -column /tmp/mock_wms_not_ready_guard_2026_05_15.db \
  "select id, task_name, target_name, status, status_reason, created_at, updated_at from tasks;"
```

## 5. 运行时观察

在未发布 initial pose 的前提下，headless 会话中持续出现以下 ready-gate 未满足证据：

- `AMCL cannot publish a pose or update the transform. Please set the initial pose...`
- `Timed out waiting for transform from base_link to map to become available`
- `Failed to activate global_costmap because transform from base_link to map did not become available before timeout`
- `Failed to bring up all requested nodes. Aborting bringup.`

补充采样结果：

- `/amcl` lifecycle：`active [3]`
- `/planner_server` lifecycle：`inactive [2]`

这说明本轮不是 action 层失败，而是执行前置 ready 条件本身未满足。

## 6. Executor 与数据库证据

executor 输出：

```text
[mock_wms_executor] outcome=execute-not-ready-timeout, mode=execute, task_id=1, target_name=station_a. Nav2 ready gate did not become ready within 20.0s. Last failure: /planner_server lifecycle state is inactive
```

SQLite 最终状态：

```text
id  task_name                   target_name  status   status_reason                                                               created_at            updated_at
--  --------------------------  -----------  -------  --------------------------------------------------------------------------  --------------------  --------------------
1   not-ready-station-a-run-01  station_a    pending  Nav2 ready gate not satisfied: /planner_server lifecycle state is inactive  2026-05-14T16:36:39Z  2026-05-14T16:37:15Z
```

这说明：

- task 没有被错误改写为 `running`
- task 没有被错误消费为 `failed` 或 `succeeded`
- task 保持 `pending`
- `status_reason` 已留下可复核原因

## 7. 不发 Goal 证据

本轮收集到的 launch 输出中，没有出现以下导航执行证据：

- `Begin navigating from current location ...`
- `Received a goal, begin computing control effort.`
- `Goal succeeded`

结合 executor 的 `execute-not-ready-timeout` 结果，可以判定当前主线确实在 ready gate 前拦住了任务，而不是先发 goal 再失败。

## 8. 结果判定

| 验证项 | 预期 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| 未注入 initial pose | 系统保持 not-ready | 持续出现 AMCL / TF not-ready warning | 通过 |
| executor ready gate | not-ready 时不得执行 | `outcome=execute-not-ready-timeout` | 通过 |
| 是否发送 goal | 不发送 | 未观察到 `Begin navigating` / `Received a goal` | 通过 |
| 任务状态 | 保持 `pending` | `status=pending` | 通过 |
| 原因留痕 | 写入 `status_reason` | 已写入 planner inactive 原因 | 通过 |

## 9. 结论与边界

本轮已经证明，当前主线在 Nav2 未 ready 时具备以下运行时保护语义：

- 不冒进发送导航 goal
- 不错误消费任务
- 通过 `pending + status_reason` 保留后续恢复空间

同时需要保持当前口径：

- 当前 SQLite 语义是 `pending + status_reason`
- 当前主线没有单独引入 `skipped` 状态
- 这是一条面向任务执行保护逻辑的最小运行时负例，不是生产级故障编排系统
