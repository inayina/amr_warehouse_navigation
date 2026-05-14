# Mock WMS HTTP API Validation

日期：`2026-05-14`

## 1. 结论

本轮已经完成最小 Mock WMS HTTP API 的真实本地验证。

验证范围只包括：

- FastAPI / uvicorn HTTP 服务
- SQLite Mock WMS 数据层
- `GET /health`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`

本轮未验证：

- Nav2 lifecycle
- `mock_wms_task_runner`
- `/navigate_to_pose`
- Gazebo 真实运动

## 2. 修改前判断

本轮主问题是：

- 当前仓库已有 SQLite Mock WMS 数据层和 CLI，但没有最小 HTTP API 暴露层

本轮改动文件：

- `scripts/mock_wms_api.py`
- `amr_warehouse_sim/mock_wms_api.py`
- `setup.py`
- `requirements.txt`
- `test/integration/test_mock_wms_http_api.py`
- `test/integration/test_mock_wms_cli_entrypoints.py`
- `docs/designs/mock_wms_http_api_plan.md`
- `docs/wms/reports/mock_wms_http_api_validation_2026_05_14.md`

## 3. 依赖与环境

本轮实际在临时虚拟环境中安装：

- `fastapi==0.136.1`
- `uvicorn==0.46.0`

说明：

- 这些是 HTTP API 运行所需的最小依赖
- `httpx` 只用于本轮本地自动化测试，不是当前 API 运行时必须依赖

本轮使用的临时数据库：

```text
/tmp/mock_wms_http_api_validation_2026_05_14.db
```

本轮使用的 task points：

```text
/home/ina/ros2_ws/src/amr_warehouse_sim/config/task_points.yaml
```

## 4. 自动化测试

执行：

```bash
PYTHONPATH=/tmp/mock_wms_api_venv/lib/python3.12/site-packages:$PYTHONPATH \
python3 -m pytest \
  test/integration/test_mock_wms_http_api.py \
  test/integration/test_mock_wms_db.py \
  test/integration/test_mock_wms_cli_entrypoints.py \
  -q
```

结果：

```text
19 passed in 0.66s
```

## 5. uvicorn 启动命令

执行：

```bash
export PATH=/tmp/mock_wms_api_venv/bin:$PATH
export MOCK_WMS_DB_PATH=/tmp/mock_wms_http_api_validation_2026_05_14.db
export MOCK_WMS_TASK_POINTS_PATH=/home/ina/ros2_ws/src/amr_warehouse_sim/config/task_points.yaml
uvicorn scripts.mock_wms_api:create_app --factory --host 127.0.0.1 --port 8010 --log-level warning
```

## 6. 手动 HTTP 验证

健康检查：

```bash
curl --noproxy '*' -sS http://127.0.0.1:8010/health
```

创建任务：

```bash
curl --noproxy '*' -sS -X POST http://127.0.0.1:8010/tasks \
  -H 'Content-Type: application/json' \
  -d '{"target_name":"station_a","task_name":"http-api-station-a"}'
```

查询任务列表和单个任务：

```bash
curl --noproxy '*' -sS http://127.0.0.1:8010/tasks
curl --noproxy '*' -sS http://127.0.0.1:8010/tasks/1
```

状态回写：

```bash
curl --noproxy '*' -sS -X PATCH http://127.0.0.1:8010/tasks/1/status \
  -H 'Content-Type: application/json' \
  -d '{"status":"running","status_reason":"HTTP executor claimed the task."}'
```

本轮确认：

- `GET /health` 会初始化 SQLite DB，并返回 `db_path` 与 `task_points_path`。
- `POST /tasks` 可以把 `station_a` 写入 `pending` task。
- `GET /tasks` 可以返回任务列表和 `count`。
- `GET /tasks/{task_id}` 可以返回单条任务。
- `PATCH /tasks/{task_id}/status` 可以完成最小状态回写。
- 未知任务返回 `404`。
- 非法目标点与非法状态返回 `400`。

## 7. 当前边界

- HTTP API 当前只暴露 SQLite Mock WMS 数据层和最小状态回写。
- HTTP API 本身不发送 Nav2 goal，不直接控制 `/cmd_vel`，不启动 Gazebo。
- `mock_wms_executor --api-base-url ...` 是后续把 HTTP task intake 接入 Nav2 execute 的入口；这不改变本 API 的职责边界。
- 本轮未引入 Web 后台、MQTT、WebSocket、多机器人调度或订单系统。

## 8. 结论

最小 Mock WMS HTTP API 可以作为当前主线的任务创建 / 查询 / 状态回写入口。它适合支撑 executor over HTTP 的下一层验证，但仍应被描述为“Mock WMS 最小 HTTP 边界”，不是完整 WMS 平台。
