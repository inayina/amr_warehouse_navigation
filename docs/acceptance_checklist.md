# Acceptance Checklist

日期：`2026-05-15`

## 1. 使用说明

这份清单面向项目经理、技术产品经理、系统集成工程师和测试人员，目标是回答两个问题：

- 当前最小闭环已经验收到什么程度
- 每一项结论可以去哪里复核

状态口径：

- `已验证`：已有自动化测试、运行时报告或两者兼有
- `已验证，边界明确`：功能已验证，但文档中同时明确写出了当前限制
- `已定义，待执行`：场景规格和入口已经落库，但仍需要继续执行并沉淀正式报告

## 2. 验收清单

| 验收项 | 预期结果 | 实际验证方式 | 当前状态 | 相关命令或文档入口 |
| --- | --- | --- | --- | --- |
| 初始化 Mock WMS 数据库 | 能创建最小 SQLite tasks 表 | CLI 手动执行 + 集成测试 | 已验证 | `ros2 run amr_warehouse_sim init_mock_wms_db --db data/mock_wms.db`；[test/integration/test_mock_wms_db.py](../test/integration/test_mock_wms_db.py) |
| 创建任务 | 能从 `config/task_points.yaml` 创建 `pending` 任务 | CLI 手动执行 + 集成测试 + HTTP API 验证 | 已验证 | `ros2 run amr_warehouse_sim create_mock_task --target station_a`；[docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md](./wms/reports/wms_task_points_readiness_report_2026_05_13.md)；[docs/wms/reports/mock_wms_http_api_validation_2026_05_14.md](./wms/reports/mock_wms_http_api_validation_2026_05_14.md) |
| 查询任务 | 能查询任务列表和单条任务 | CLI 表格输出 + HTTP API 手测 + 集成测试 | 已验证 | `ros2 run amr_warehouse_sim list_mock_tasks`；`curl --noproxy '*' -sS http://127.0.0.1:8000/tasks`；[test/integration/test_mock_wms_http_api.py](../test/integration/test_mock_wms_http_api.py) |
| HTTP API 最小边界 | `GET /health`、`POST /tasks`、`GET /tasks`、`GET /tasks/{task_id}`、`PATCH /tasks/{task_id}/status` 可用 | 本地 `uvicorn + curl` 手测 + 集成测试 | 已验证，边界明确 | [docs/wms/reports/mock_wms_http_api_validation_2026_05_14.md](./wms/reports/mock_wms_http_api_validation_2026_05_14.md)；[docs/guides/mock_wms_http_api_manual_test_guide.md](./guides/mock_wms_http_api_manual_test_guide.md) |
| executor 获取最早一条 pending task | 单条 executor 能识别并处理最早一条 pending task | 自动化契约测试 + 运行时 dry-run / execute 报告 | 已验证，边界明确 | `ros2 run amr_warehouse_sim mock_wms_executor --dry-run`；[test/integration/test_mock_wms_executor_contract.py](../test/integration/test_mock_wms_executor_contract.py)；[docs/wms/reports/mock_wms_executor_execute_validation_2026_05_13.md](./wms/reports/mock_wms_executor_execute_validation_2026_05_13.md) |
| task runner 执行任务 | 顺序 runner 能按队列顺序执行任务，并在成功后消费任务 | 自动化契约测试 + live ROS / Nav2 报告 + queue/restart 回归 | 已验证 | `ros2 run amr_warehouse_sim mock_wms_task_runner --execute --max-tasks 2`；[test/integration/test_mock_wms_task_runner.py](../test/integration/test_mock_wms_task_runner.py)；[docs/wms/reports/mock_wms_task_runner_live_validation_2026_05_13.md](./wms/reports/mock_wms_task_runner_live_validation_2026_05_13.md)；[docs/wms/reports/mock_wms_queue_restart_regression_2026_05_15.md](./wms/reports/mock_wms_queue_restart_regression_2026_05_15.md) |
| 队列 / 重启回归 | 两条任务场景下，第 1 条可先成功，重启后 not-ready 不错误消费剩余任务，恢复后只继续剩余 `pending` | fresh-session live Nav2 + task runner 三阶段回归 | 已验证，边界明确 | [docs/wms/reports/mock_wms_queue_restart_regression_2026_05_15.md](./wms/reports/mock_wms_queue_restart_regression_2026_05_15.md) |
| Nav2 lifecycle ready 检查 | 发送 goal 前会检查 `/map_server`、`/amcl`、`/planner_server`、`/controller_server`、`/bt_navigator` readiness | ready report + executor contract + task runner live validation | 已验证 | `ros2 lifecycle get /map_server` 等；[docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md](./wms/reports/wms_task_points_readiness_report_2026_05_13.md)；[test/integration/test_mock_wms_executor_contract.py](../test/integration/test_mock_wms_executor_contract.py) |
| `/navigate_to_pose` action server 可用性检查 | 只有 action server 可用时才允许进入 execute | ready report + executor contract | 已验证 | `ros2 action info /navigate_to_pose`；[docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md](./wms/reports/wms_task_points_readiness_report_2026_05_13.md)；[test/integration/test_mock_wms_executor_contract.py](../test/integration/test_mock_wms_executor_contract.py) |
| 导航成功后状态更新为 `SUCCEEDED` | 成功任务最终回写为 `succeeded`，并带有 Nav2 结果原因 | task runner live 报告 + executor contract | 已验证 | [docs/wms/reports/mock_wms_task_runner_live_validation_2026_05_13.md](./wms/reports/mock_wms_task_runner_live_validation_2026_05_13.md)；[test/integration/test_mock_wms_executor_contract.py](../test/integration/test_mock_wms_executor_contract.py) |
| Nav2 未 ready 时不冒进发送 goal，并记录原因 | 当前主线不会强行发送 goal；会保留任务并写入原因 | readiness report + executor execute validation + runtime negative case + contract tests | 已验证，边界明确 | 当前 SQLite 口径是 `pending + status_reason`，而不是单独 `skipped` 状态；[docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md](./wms/reports/wms_task_points_readiness_report_2026_05_13.md)；[docs/wms/reports/mock_wms_executor_execute_validation_2026_05_13.md](./wms/reports/mock_wms_executor_execute_validation_2026_05_13.md)；[docs/wms/reports/mock_wms_not_ready_guard_runtime_validation_2026_05_15.md](./wms/reports/mock_wms_not_ready_guard_runtime_validation_2026_05_15.md) |
| Headless Nav2 ready-gate 集成验证 | fresh session 下 `/map`、`/scan_filtered`、`map -> odom`、5 个 lifecycle nodes 和 `/navigate_to_pose` 在统一时窗内 ready | fresh-session headless live Nav2 运行报告 | 已验证 | [docs/wms/reports/headless_nav2_ready_integration_validation_2026_05_15.md](./wms/reports/headless_nav2_ready_integration_validation_2026_05_15.md)；[test/scenarios/headless_nav2_ready_integration.md](../test/scenarios/headless_nav2_ready_integration.md) |
| 固定任务点成功矩阵回归 | `station_a`、`station_b`、`shelf_1`、`shelf_2` 都能留下可复核的 `SUCCEEDED / SKIPPED / ABORTED` 证据 | fresh-session live Nav2 矩阵回归 + historical readiness 报告 | 已验证，边界明确 | [docs/wms/reports/fixed_task_points_success_matrix_regression_2026_05_15.md](./wms/reports/fixed_task_points_success_matrix_regression_2026_05_15.md)；[docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md](./wms/reports/wms_task_points_readiness_report_2026_05_13.md)；[test/scenarios/fixed_task_points_success_matrix_regression.md](../test/scenarios/fixed_task_points_success_matrix_regression.md) |
| HTTP API -> executor -> Nav2 -> HTTP 状态回写端到端闭环 | 能通过 HTTP 创建任务、由 executor 消费并接回 Nav2，再通过 HTTP 查询最终状态 | headless live Nav2 + 本地 `uvicorn` + HTTP executor 运行报告 | 已验证 | [docs/wms/reports/mock_wms_http_executor_end_to_end_validation_2026_05_14.md](./wms/reports/mock_wms_http_executor_end_to_end_validation_2026_05_14.md)；[test/scenarios/mock_wms_http_executor_end_to_end.md](../test/scenarios/mock_wms_http_executor_end_to_end.md) |
| 文档与测试报告可追溯 | README、设计文档、测试报告、验收清单之间可以互相定位 | 文档索引检查 | 已验证 | [docs/README.md](./README.md)；[README.md](../README.md)；[test/README.md](../test/README.md) |

## 3. 当前验收结论

- 当前项目已经满足“任务创建 -> 查询 -> 执行 -> 状态回写 -> 报告留痕”的最小闭环展示要求。
- 当前项目的验收表述应聚焦“物流机器人任务执行与导航验证案例”，而不是完整 WMS 或生产调度系统。
- 当前剩余风险主要是 fresh session 下的 ready gate 波动边界，这已经在运行时报告中如实保留。
