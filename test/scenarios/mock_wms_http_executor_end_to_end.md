# Scenario: Mock WMS HTTP Executor End-To-End

这个场景用于验证当前主线最完整的一条任务闭环：

```text
HTTP API
-> create task
-> mock_wms_executor --api-base-url ... --execute
-> Nav2 ready gate
-> NavigateToPose
-> HTTP status writeback
```

它属于当前主线的关键运行时验证场景，因为它把“最小 Mock WMS 任务入口”和“当前 Nav2 执行主线”真正接到了一起。

## 场景目标

- 验证 FastAPI / uvicorn 的最小 Mock WMS HTTP API 可以创建 `pending` task
- 验证 `mock_wms_executor --api-base-url ... --execute` 可以通过 HTTP 获取任务并接回 Nav2 execute
- 验证任务最终状态可以通过 HTTP 查询回写结果

## 适用范围

- 当前主线：V3 最小 Mock WMS HTTP task intake + Nav2 execute
- HTTP API 入口：
  `uvicorn scripts.mock_wms_api:create_app --factory`
- 执行入口：
  `ros2 run amr_warehouse_sim mock_wms_executor --api-base-url ... --execute`
- 推荐目标点：
  `station_a`

## 不在本场景内

- 不验证多任务顺序消费
- 不验证生产级认证、账号、权限、Web 后台
- 不把 HTTP API 声明为完整 WMS 平台

## 前置条件

- 已完成 `test/scenarios/headless_nav2_ready_integration.md` 或同等 ready 验证
- 当前环境已安装 `fastapi`、`uvicorn`
- 已完成编译并 `source install/setup.bash`
- 建议使用独立临时数据库，例如：
  `/tmp/mock_wms_http_executor_e2e.db`
- 建议使用独立端口，例如：
  `127.0.0.1:8010`

## 执行步骤

### A. 准备 headless Nav2 会话

1. 启动：
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
2. 发布 initial pose：
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
3. 确认 ready gate 已满足：
   `5/5 lifecycle active`
   `map -> odom` 可用
   `/navigate_to_pose` action server 数量为 `1`

### B. 启动 HTTP API

1. 设置：
   `MOCK_WMS_DB_PATH=/tmp/mock_wms_http_executor_e2e.db`
   `MOCK_WMS_TASK_POINTS_PATH=$PWD/config/task_points.yaml`
2. 启动：
   `uvicorn scripts.mock_wms_api:create_app --factory --host 127.0.0.1 --port 8010 --log-level warning`
3. 健康检查：
   `curl --noproxy '*' -sS http://127.0.0.1:8010/health`

### C. 通过 HTTP 创建任务

1. 执行：
   `curl --noproxy '*' -sS -X POST http://127.0.0.1:8010/tasks -H 'Content-Type: application/json' -d '{"target_name":"station_a","task_name":"http-e2e-station-a"}'`
2. 确认任务初始状态为：
   `pending`
3. 执行：
   `curl --noproxy '*' -sS http://127.0.0.1:8010/tasks`

### D. 通过 HTTP executor 执行任务

1. 执行：
   `ros2 run amr_warehouse_sim mock_wms_executor --api-base-url http://127.0.0.1:8010 --execute --ready-timeout 60 --navigation-timeout 180`
2. 观察 executor 是否：
   先通过 ready gate
   再发送 `NavigateToPose`
   最后通过 HTTP 回写任务状态

### E. 查询最终任务状态

1. 执行：
   `curl --noproxy '*' -sS http://127.0.0.1:8010/tasks/1`
2. 记录最终状态：
   `succeeded`
   或
   `failed`
   或
   `pending + status_reason`

## 建议记录的指标

- `http_health_ok`
- `task_created`
- `initial_http_status`
- `goal_sent`
- `final_http_status`
- `status_reason`
- `completion_time`

## 最低通过标准

- `GET /health` 返回 `200`
- `POST /tasks` 成功创建 `pending` task
- executor 能通过 HTTP 获取最早一条 `pending` task
- 只有在 ready gate 满足后才发送 goal
- 最终状态可通过 `GET /tasks/{task_id}` 查询到

## 结果判定建议

- `Pass`
  HTTP create/query、executor execute、Nav2 goal 和 HTTP status writeback 全部打通
- `Needs Investigation`
  HTTP create/query 正常，但 execute 过程中出现 ready gate 波动或状态回写异常
- `Fail`
  API 无法启动、HTTP 任务无法被 executor 消费，或最终状态无法回写

## 建议保留的证据

- `curl /health` 输出
- `curl POST /tasks` 输出
- executor 终端输出
- `curl /tasks/1` 最终输出
- 可选：launch 日志、屏幕录制

## 结果记录模板

| Run ID | Target | Initial HTTP Status | Goal Sent | Final HTTP Status | Status Reason | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 001 | `station_a` |  |  |  |  |  |

## 常见失败归因方向

- HTTP API 正常，但 executor 不消费任务
  优先检查 `--api-base-url`、`/tasks` 返回结构、任务状态是否为 `pending`
- executor 长时间不过 ready gate
  优先检查 headless Nav2 ready、initial pose、`map -> odom` 和 action server
- 状态回写缺失
  优先检查 `PATCH /tasks/{task_id}/status`、API 进程日志和 HTTP 可达性
