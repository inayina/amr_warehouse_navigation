# Mock WMS HTTP API Plan

日期：`2026-05-14`

## 1. 本轮主问题

本轮只解决一个明确问题：

- 为当前 SQLite Mock WMS 数据层新增一个最小 FastAPI HTTP API 暴露层

本轮不解决 Nav2 执行、不做调度系统、不引入前端或消息系统。

## 2. 修改前判断

当前仓库已经具备以下能力：

- `scripts/mock_wms_db_common.py`：SQLite 数据层公共逻辑
- `scripts/init_mock_wms_db.py`：初始化任务表
- `scripts/create_mock_task.py`：从 `config/task_points.yaml` 创建 `pending` task
- `scripts/list_mock_tasks.py`：列出当前任务

当前缺口是：

- 没有最小 HTTP 服务把这些能力暴露为 REST API
- 当前主线文档也没有一份专门的 HTTP API 设计与验证记录

## 3. 本轮改动文件

- `scripts/mock_wms_api.py`
- `amr_warehouse_sim/mock_wms_api.py`
- `setup.py`
- `requirements.txt`
- `test/integration/test_mock_wms_http_api.py`
- `test/integration/test_mock_wms_cli_entrypoints.py`
- `docs/wms/reports/mock_wms_http_api_validation_2026_05_14.md`

## 4. 每个改动的目的

- `scripts/mock_wms_api.py`
  提供最小 FastAPI 服务，优先复用 `initialize_database()`、`create_task()`、`list_tasks()`
- `amr_warehouse_sim/mock_wms_api.py`
  延续当前包入口桥接模式，避免把业务逻辑搬离 `scripts/`
- `setup.py`
  注册 `mock_wms_api` console entrypoint，并声明最小 Python 依赖
- `requirements.txt`
  记录 HTTP API 所需的最小依赖：`fastapi`、`uvicorn`
- `test/integration/test_mock_wms_http_api.py`
  覆盖 `GET /health`、`POST /tasks`、`GET /tasks`、`GET /tasks/{task_id}`
`docs/wms/reports/mock_wms_http_api_validation_2026_05_14.md`
  记录 `uvicorn` 与 `curl` 的真实验证命令和返回结果

## 5. 接口范围

本轮只实现以下接口：

- `GET /health`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`

### 5.1 `GET /health`

目的：

- 确认 HTTP 服务进程可用
- 确认 SQLite 路径与 task points 路径已解析

预期现象：

- 返回 `200 OK`
- 返回 `status=ok`

### 5.2 `POST /tasks`

目的：

- 复用当前数据层逻辑创建一条 `pending` task

请求体：

```json
{
  "target_name": "station_a",
  "task_name": "optional-name"
}
```

预期现象：

- 合法目标点返回 `201 Created`
- 非法目标点返回 `400`

### 5.3 `GET /tasks`

目的：

- 返回当前 SQLite 中的全部任务

预期现象：

- 返回 `count`
- 返回 `tasks` 数组

### 5.4 `GET /tasks/{task_id}`

目的：

- 查询单条任务详情

预期现象：

- 已存在任务返回 `200`
- 不存在任务返回 `404`

## 6. 明确不做

- 不修改 `launch/navigation.launch.py`
- 不修改 `config/nav2_params.yaml`
- 不接入 `mock_wms_task_runner` 的真实导航执行
- 不引入 MQTT / WebSocket / 前端页面
- 不重构现有 SQLite / CLI 脚本
- 不把 `future_extensions/` 接回当前主线

## 7. 验证方式

本轮验证只检查：

1. `uvicorn` 能否启动 FastAPI 服务
2. `curl` 能否打通四个接口
3. SQLite 结果是否与现有数据层一致

本轮不验证：

- Gazebo
- AMCL
- Nav2 lifecycle
- `/navigate_to_pose`
- 真实机器人运动
