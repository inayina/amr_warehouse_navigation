# Mock WMS HTTP API Manual Test Guide

日期：`2026-05-14`

## 1. 目的

这份文档用于帮助你**手动过一遍**当前最小 Mock WMS HTTP API。

本轮只验证：

- `GET /health`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`

本轮不验证：

- Nav2 execute
- `mock_wms_task_runner`
- Gazebo / 地图 / robot motion
- MQTT / WebSocket / Web 后台

## 2. 适用范围

当前这层 HTTP API 只负责把现有 SQLite Mock WMS 数据层暴露为最小 REST 接口。

它当前只做两类事情：

- 创建任务
- 查询任务

它当前不做：

- 调用 Nav2 发 goal
- 驱动真实导航
- 提供完整 WMS 调度能力

## 3. 前置条件

在开始前，先确认：

- 当前目录是仓库根目录：`~/ros2_ws/src/amr_warehouse_sim`
- `.venv` 已创建并装好 `fastapi`、`uvicorn`
- `config/task_points.yaml` 存在

建议先做一次最小自检：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
source .venv/bin/activate
python -m amr_warehouse_sim.mock_wms_api --help
```

如果这条命令能正常打印帮助信息，再继续后面的手动测试。

## 4. 推荐测试环境

为了避免污染仓库里的默认数据库，建议本轮手测使用一个临时数据库文件：

```text
/tmp/mock_wms_http_manual_test.db
```

如果你想重复多跑几轮，建议每轮开始前先删掉旧文件：

```bash
rm -f /tmp/mock_wms_http_manual_test.db
```

## 5. 启动服务

开第一个终端，执行：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
source .venv/bin/activate
export MOCK_WMS_DB_PATH=/tmp/mock_wms_http_manual_test.db
export MOCK_WMS_TASK_POINTS_PATH=$PWD/config/task_points.yaml
uvicorn scripts.mock_wms_api:create_app --factory --host 127.0.0.1 --port 8000 --log-level warning
```

说明：

- `MOCK_WMS_DB_PATH` 指向本轮手测临时数据库
- `MOCK_WMS_TASK_POINTS_PATH` 指向当前主线 `config/task_points.yaml`
- `--factory` 表示由 `uvicorn` 直接调用 `create_app()`

服务启动后，这个终端保持不动，不要关闭。

## 6. 手动测试步骤

开第二个终端，进入仓库根目录：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
```

### 6.1 `GET /health`

执行：

```bash
curl --noproxy '*' -i -sS http://127.0.0.1:8000/health
```

预期：

- HTTP 状态码是 `200 OK`
- 返回 JSON 中包含：
  - `status: ok`
  - `db_path: /tmp/mock_wms_http_manual_test.db`
  - `task_points_path: .../config/task_points.yaml`

### 6.2 `GET /tasks` 空库检查

第一次启动、且数据库为空时，先执行：

```bash
curl --noproxy '*' -i -sS http://127.0.0.1:8000/tasks
```

预期：

- HTTP 状态码是 `200 OK`
- 返回 JSON 中：
  - `count` 为 `0`
  - `tasks` 为 `[]`

### 6.3 `POST /tasks`

执行：

```bash
curl --noproxy '*' -i -sS -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"target_name":"station_a","task_name":"manual-http-task-station-a"}'
```

预期：

- HTTP 状态码是 `201 Created`
- 返回 JSON 中：
  - `id` 为正整数，首次通常是 `1`
  - `task_name` 为 `manual-http-task-station-a`
  - `target_name` 为 `station_a`
  - `frame_id` 为 `map`
  - `status` 为 `pending`

### 6.4 `GET /tasks`

执行：

```bash
curl --noproxy '*' -i -sS http://127.0.0.1:8000/tasks
```

预期：

- HTTP 状态码是 `200 OK`
- 返回 JSON 中：
  - `count` 为 `1`
  - `tasks[0]` 就是刚创建的任务

### 6.5 `GET /tasks/{task_id}`

如果上一步返回的 `id` 是 `1`，执行：

```bash
curl --noproxy '*' -i -sS http://127.0.0.1:8000/tasks/1
```

预期：

- HTTP 状态码是 `200 OK`
- 返回 JSON 与 `POST /tasks` 的创建结果一致

## 7. 建议补测的错误路径

下面两条虽然不是主路径，但很值得手动过一遍。

### 7.1 查询不存在的 task

执行：

```bash
curl --noproxy '*' -i -sS http://127.0.0.1:8000/tasks/999
```

预期：

- HTTP 状态码是 `404 Not Found`
- 返回 JSON：

```json
{"detail":"Task id=999 was not found."}
```

### 7.2 创建非法目标点

执行：

```bash
curl --noproxy '*' -i -sS -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"target_name":"start_zone"}'
```

预期：

- HTTP 状态码是 `400 Bad Request`
- 返回 JSON 的 `detail` 中包含：
  `validated task targets`

原因：

- `start_zone` 当前只作为 initial pose 使用，不是当前 V3 Mock WMS 允许的任务目标点

## 8. 通过标准

如果下面这些现象都成立，可以认为这轮 HTTP 手测通过：

- `uvicorn` 能正常启动服务
- `GET /health` 返回 `200`
- 空库时 `GET /tasks` 返回 `count=0`
- `POST /tasks` 能成功创建一条 `pending` task
- 创建后 `GET /tasks` 能看到同一条任务
- `GET /tasks/{task_id}` 能正确读回该任务
- `GET /tasks/999` 返回 `404`
- 非法目标点创建返回 `400`

## 9. 常见问题

### 9.1 `curl` 连不上 `127.0.0.1:8000`

优先检查：

- 第一个终端里的 `uvicorn` 是否还在运行
- 端口是否被别的程序占用
- 当前是否开了代理；如果有代理，优先保留 `--noproxy '*'`

### 9.2 启动时报 `ModuleNotFoundError: fastapi` 或 `uvicorn`

说明 `.venv` 里的依赖还没装好。

先执行：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
source .venv/bin/activate
pip install -r requirements.txt
```

### 9.3 `POST /tasks` 返回 `400`

优先检查：

- `target_name` 是否是当前允许点位：
  `candidate_dock_a` / `dock_a` / `station_a` / `station_b` / `shelf_1` / `shelf_2`
- `config/task_points.yaml` 是否存在
- `task_name` 是否传了空字符串

## 10. 收尾

手动测试完成后：

1. 回到启动 `uvicorn` 的终端
2. 按 `Ctrl+C` 停掉服务
3. 如无保留需要，可删除临时数据库

```bash
rm -f /tmp/mock_wms_http_manual_test.db
```

## 11. 相关文档

- [../designs/mock_wms_http_api_plan.md](../designs/mock_wms_http_api_plan.md)
- [../wms/reports/mock_wms_http_api_validation_2026_05_14.md](../wms/reports/mock_wms_http_api_validation_2026_05_14.md)
- [../designs/mock_wms_design.md](../designs/mock_wms_design.md)
