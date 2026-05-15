# Mock WMS Queue And Restart Regression

日期：`2026-05-15`

## 1. 结论

本轮已经完成当前主线一次“两条任务队列 + 重启恢复”的真实运行时回归，结论为：`Pass`。

本轮确认：

- 同一 SQLite 队列中的第 1 条任务可以先成功执行
- runner 退出后，数据库中间态与预期一致
- 重新启动但不注入 initial pose 时，runner 会把剩余任务拦在 ready gate 前
- 再次 fresh restart 并恢复 initial pose 后，runner 只会继续处理剩余 `pending` 任务
- 已经 `succeeded` 的历史任务不会被重复消费

## 2. 修改前判断

本轮主问题不是新增队列功能，而是把当前主线已有的单队列执行语义补成一份更像“可持续运行系统”的运行时报告。

本轮文档改动文件：

- `docs/wms/reports/mock_wms_queue_restart_regression_2026_05_15.md`
- `docs/acceptance_checklist.md`

本轮未修改：

- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- `config/task_points.yaml`
- Mock WMS task runner / executor 代码逻辑

## 3. 场景设计

提交版本：

```text
f679732
```

本轮使用同一个 SQLite DB：

```text
/tmp/mock_wms_queue_restart_regression_2026_05_15.db
```

初始队列包含两条任务：

1. `queue-restart-station-a-run-01`
2. `queue-restart-station-b-run-01`

之所以把第二阶段设计成“not-ready 保留 pending”，而不是“第 2 条立即 failed”，是因为这更符合当前主线真实语义：

- ready gate 不满足时，任务不会被消费
- 数据库保留 `pending + status_reason`
- 恢复后可以继续处理剩余任务

这正是系统集成视角更关心的“持续运行与恢复”能力。

## 4. 执行方法

三阶段均使用 fresh headless Nav2 会话：

```bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
```

统一起始位姿命令：

```bash
python3 scripts/publish_initial_pose.py --preset start_zone --wait-for-subscribers 30
```

runner 命令：

```bash
ros2 run amr_warehouse_sim mock_wms_task_runner \
  --db /tmp/mock_wms_queue_restart_regression_2026_05_15.db \
  --execute \
  --max-tasks 1 \
  --ready-timeout 60 \
  --navigation-timeout 180
```

第二阶段命令：

```bash
ros2 run amr_warehouse_sim mock_wms_task_runner \
  --db /tmp/mock_wms_queue_restart_regression_2026_05_15.db \
  --execute \
  --max-tasks 1 \
  --ready-timeout 20 \
  --ready-poll-interval 2 \
  --navigation-timeout 180
```

第三阶段命令：

```bash
ros2 run amr_warehouse_sim mock_wms_task_runner \
  --db /tmp/mock_wms_queue_restart_regression_2026_05_15.db \
  --execute \
  --ready-timeout 60 \
  --navigation-timeout 180
```

三阶段 launch 日志目录：

- Phase A：
  `/tmp/mock_wms_executor_validation_ros_logs/2026-05-15-00-41-10-859819-ina-Gen6-534912`
- Phase B：
  `/tmp/mock_wms_executor_validation_ros_logs/2026-05-15-00-43-01-349717-ina-Gen6-536042`
- Phase C：
  `/tmp/mock_wms_executor_validation_ros_logs/2026-05-15-00-44-23-433989-ina-Gen6-537016`

## 5. 初始队列状态

初始数据库状态：

```text
id  task_name                       target_name  status
--  ------------------------------  -----------  -------
1   queue-restart-station-a-run-01  station_a    pending
2   queue-restart-station-b-run-01  station_b    pending
```

## 6. Phase A：先执行第 1 条任务

Phase A 条件：

- fresh session
- 已注入 `start_zone` initial pose
- `--max-tasks 1`

runner 输出：

```text
[mock_wms_executor] outcome=succeeded, mode=execute, task_id=1, target_name=station_a. NavigateToPose result: SUCCEEDED.
[mock_wms_task_runner] mode=execute, executor_runs=1, task_runs=1, consumed_tasks=1, succeeded_tasks=1, failed_tasks=0, stop_reason=max-tasks-reached, last_outcome=succeeded.
```

headless Nav2 关键证据：

- `Begin navigating from current location (0.02, 0.02) to (-5.30, -5.80)`
- `Received a goal, begin computing control effort.`
- `Reached the goal!`
- `Goal succeeded`

Phase A 后数据库状态：

```text
id  task_name                       target_name  status     status_reason
--  ------------------------------  -----------  ---------  ---------------------------------
1   queue-restart-station-a-run-01  station_a    succeeded  NavigateToPose result: SUCCEEDED.
2   queue-restart-station-b-run-01  station_b    pending
```

说明：

- 这一步证明队列中的第 1 条任务已被正确消费
- 第 2 条任务仍保留为剩余 `pending`

## 7. Phase B：重启后不注入 initial pose

Phase B 条件：

- fresh restart
- 不发布 initial pose
- 对同一个 DB 再次运行 runner

runner 输出：

```text
[mock_wms_executor] outcome=execute-not-ready-timeout, mode=execute, task_id=2, target_name=station_b. Nav2 ready gate did not become ready within 20.0s. Last failure: /planner_server lifecycle state is timeout
[mock_wms_task_runner] mode=execute, executor_runs=1, task_runs=1, consumed_tasks=0, succeeded_tasks=0, failed_tasks=0, stop_reason=ready-gate-timeout, last_outcome=execute-not-ready-timeout.
[ros2run]: Process exited with failure 1
```

headless Nav2 关键证据：

- 持续出现 `Please set the initial pose...`
- 持续出现 `Timed out waiting for transform from base_link to map ...`
- 本阶段没有出现 `Begin navigating`
- 本阶段没有出现 `Received a goal`
- 本阶段没有出现 `Goal succeeded`

Phase B 后数据库状态：

```text
id  task_name                       target_name  status     status_reason
--  ------------------------------  -----------  ---------  -------------------------------------------------------------------------
1   queue-restart-station-a-run-01  station_a    succeeded  NavigateToPose result: SUCCEEDED.
2   queue-restart-station-b-run-01  station_b    pending    Nav2 ready gate not satisfied: /planner_server lifecycle state is timeout
```

说明：

- runner 没有把第 2 条任务错误消费掉
- 队列在重启后的 not-ready 条件下仍保留了继续恢复的空间

## 8. Phase C：恢复后只继续剩余任务

Phase C 条件：

- fresh restart
- 重新发布 `start_zone` initial pose
- 对同一个 DB 再次运行 runner

runner 输出：

```text
[mock_wms_executor] outcome=succeeded, mode=execute, task_id=2, target_name=station_b. NavigateToPose result: SUCCEEDED.
[mock_wms_executor] outcome=no-pending-task, mode=execute, task_id=n/a, target_name=n/a. No pending tasks found.
[mock_wms_task_runner] mode=execute, executor_runs=2, task_runs=1, consumed_tasks=1, succeeded_tasks=1, failed_tasks=0, stop_reason=queue-empty, last_outcome=no-pending-task.
```

headless Nav2 关键证据：

- `Begin navigating from current location (0.01, 0.02) to (5.00, -4.80)`
- `Received a goal, begin computing control effort.`
- `Reached the goal!`
- `Goal succeeded`

Phase C 最终数据库状态：

```text
id  task_name                       target_name  status     status_reason
--  ------------------------------  -----------  ---------  ---------------------------------
1   queue-restart-station-a-run-01  station_a    succeeded  NavigateToPose result: SUCCEEDED.
2   queue-restart-station-b-run-01  station_b    succeeded  NavigateToPose result: SUCCEEDED.
```

说明：

- Phase C 只处理了 `task_id=2`
- 之后 executor 再查队列时直接得到 `no-pending-task`
- 这就是“只继续剩余 pending”的直接证据

## 9. 结果判定

| 验证项 | 预期 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| 第 1 条任务执行 | 成功并消费队首任务 | `task_id=1` 成功，`station_b` 仍 `pending` | 通过 |
| runner 退出后的中间态 | 数据库状态正确 | 一条 `succeeded` + 一条 `pending` | 通过 |
| 重启后 not-ready 保护 | 不冒进消费剩余任务 | `consumed_tasks=0`，`task_id=2` 保持 `pending` | 通过 |
| pending 原因留痕 | 写入恢复前原因 | `status_reason` 已写入 ready-gate timeout | 通过 |
| 恢复后继续执行 | 只处理剩余 `pending` | Phase C 只执行 `task_id=2` | 通过 |
| 队列收尾 | 剩余任务执行后返回空队列 | `last_outcome=no-pending-task` | 通过 |

## 10. 结论与边界

本轮已经证明，当前主线具备以下可复核的队列与重启语义：

- 单队列可顺序执行
- 重启后状态可追溯
- not-ready 条件下不会把剩余任务错误消费
- 恢复后可以继续处理剩余 `pending`

同时仍需保持当前口径：

- 这不是生产级常驻调度系统
- 这不是多机器人调度
- 当前恢复语义依赖 `pending + status_reason`，而不是复杂的重试编排机制
