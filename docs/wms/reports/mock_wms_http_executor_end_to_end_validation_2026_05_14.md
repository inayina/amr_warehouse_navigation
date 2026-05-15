# Mock WMS HTTP Executor End-To-End Validation

日期：`2026-05-14`

## 1. 结论

本轮已经完成当前主线最小闭环的一次真实端到端验证，结论为：`Pass`。

本轮实际打通的链路是：

```text
HTTP API
-> create task
-> mock_wms_executor --api-base-url ... --execute
-> Nav2 ready gate
-> NavigateToPose
-> HTTP status writeback
```

本轮同时确认：

- 本次验证使用了 fresh headless Nav2 会话
- 本次验证没有修改 `navigation.launch.py`
- 本次验证没有修改 `config/nav2_params.yaml`
- 本次验证没有修改地图、world 或 robot model

## 2. 修改前判断

本轮主问题不是新增功能，而是把已经实际跑通的端到端场景沉淀成正式报告，便于后续在 README、验收清单、面试讲解和 GitHub 展示中复核。

本轮文档改动文件：

- `docs/wms/reports/mock_wms_http_executor_end_to_end_validation_2026_05_14.md`
- `docs/acceptance_checklist.md`

目的：

- 记录真实运行命令、关键输出和最终结论
- 把“HTTP API -> executor -> Nav2 -> HTTP 状态回写”从场景定义同步为已验证项

## 3. 验证范围与边界

本轮验证范围：

- headless `navigation.launch.py` 会话
- `publish_initial_pose --preset start_zone`
- FastAPI / uvicorn Mock WMS HTTP API
- `POST /tasks`、`GET /health`、`GET /tasks`、`GET /tasks/{task_id}`
- `mock_wms_executor --api-base-url ... --execute`
- Nav2 `NavigateToPose`
- HTTP 状态回写

本轮不在范围内：

- 多任务顺序消费
- 多机器人调度
- 生产级账号、权限、Web 后台
- 真实硬件接入

## 4. 环境与命令

提交版本：

```text
f679732
```

本轮使用：

- ROS 2 Jazzy
- headless Nav2 launch：`use_gz_gui:=false use_rviz:=false`
- 本地 HTTP API：`127.0.0.1:8010`
- 临时数据库：`/tmp/mock_wms_http_executor_e2e.db`
- task points：`/home/ina/ros2_ws/src/amr_warehouse_sim/config/task_points.yaml`

执行命令摘要：

```bash
source /opt/ros/jazzy/setup.bash
source /home/ina/ros2_ws/install/setup.bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
```

```bash
python3 scripts/publish_initial_pose.py --preset start_zone --wait-for-subscribers 30
```

```bash
. .venv/bin/activate
export MOCK_WMS_DB_PATH=/tmp/mock_wms_http_executor_e2e.db
export MOCK_WMS_TASK_POINTS_PATH=/home/ina/ros2_ws/src/amr_warehouse_sim/config/task_points.yaml
uvicorn scripts.mock_wms_api:create_app --factory --host 127.0.0.1 --port 8010 --log-level warning
```

```bash
curl --noproxy '*' -sS http://127.0.0.1:8010/health
curl --noproxy '*' -sS -X POST http://127.0.0.1:8010/tasks \
  -H 'Content-Type: application/json' \
  -d '{"target_name":"station_a","task_name":"http-e2e-station-a"}'
curl --noproxy '*' -sS http://127.0.0.1:8010/tasks/1
```

```bash
ros2 run amr_warehouse_sim mock_wms_executor \
  --api-base-url http://127.0.0.1:8010 \
  --execute \
  --ready-timeout 60 \
  --navigation-timeout 180
```

## 5. Ready Gate 快照

发布 initial pose 之后，本轮确认以下条件满足：

| 检查项 | 实际结果 |
| --- | --- |
| `/map_server` lifecycle | `active [3]` |
| `/amcl` lifecycle | `active [3]` |
| `/planner_server` lifecycle | `active [3]` |
| `/controller_server` lifecycle | `active [3]` |
| `/bt_navigator` lifecycle | `active [3]` |
| `map -> odom` TF | 可查询到有效变换 |
| `/navigate_to_pose` action server | `1` 个 server，由 `/bt_navigator` 提供 |

补充说明：

- 在 initial pose 发布前，AMCL / global costmap 出现了预期内的 `Please set the initial pose...` 与缺少 `map` 相关 warning。
- 发布 `start_zone` initial pose 后，系统恢复到可执行状态，这与当前主线预期一致。

## 6. HTTP API 验证结果

健康检查返回：

```json
{"status":"ok","db_path":"/tmp/mock_wms_http_executor_e2e.db","task_points_path":"/home/ina/ros2_ws/src/amr_warehouse_sim/config/task_points.yaml"}
```

创建任务返回：

```json
{"id":1,"task_name":"http-e2e-station-a","target_name":"station_a","frame_id":"map","x":-5.3,"y":-5.8,"yaw":3.14,"status":"pending","status_reason":null,"created_at":"2026-05-14T16:00:11Z","updated_at":"2026-05-14T16:00:11Z"}
```

执行前查询单条任务返回：

```json
{"id":1,"task_name":"http-e2e-station-a","target_name":"station_a","frame_id":"map","x":-5.3,"y":-5.8,"yaw":3.14,"status":"pending","status_reason":null,"created_at":"2026-05-14T16:00:11Z","updated_at":"2026-05-14T16:00:11Z"}
```

说明：

- 本轮有一次并行执行的 `GET /tasks` 与 `POST /tasks` 同时触发，列表瞬时返回了 `count=0`。
- 随后的顺序重查已经确认任务持久化成功，因此这属于本次取证步骤的竞态，不是当前主线功能结论。

## 7. Executor 与 Nav2 执行结果

executor 输出：

```text
[mock_wms_executor] outcome=succeeded, mode=http-execute, task_id=1, target_name=station_a. NavigateToPose result: SUCCEEDED.
```

headless Nav2 会话中可见的关键运行证据包括：

- `initialPoseReceived` 已出现
- `Managed nodes are active` 已出现
- `Begin navigating from current location (0.01, 0.03) to (-5.30, -5.80)`
- `Received a goal, begin computing control effort.`
- `Reached the goal!`
- `Goal succeeded`

这说明本轮不是只验证 HTTP create/query，而是确实由 HTTP executor 接回了 Nav2 action execute。

## 8. 最终状态回写结果

执行完成后，`GET /tasks/1` 返回：

```json
{"id":1,"task_name":"http-e2e-station-a","target_name":"station_a","frame_id":"map","x":-5.3,"y":-5.8,"yaw":3.14,"status":"succeeded","status_reason":"NavigateToPose result: SUCCEEDED.","created_at":"2026-05-14T16:00:11Z","updated_at":"2026-05-14T16:01:08Z"}
```

`GET /tasks` 返回：

```json
{"count":1,"tasks":[{"id":1,"task_name":"http-e2e-station-a","target_name":"station_a","frame_id":"map","x":-5.3,"y":-5.8,"yaw":3.14,"status":"succeeded","status_reason":"NavigateToPose result: SUCCEEDED.","created_at":"2026-05-14T16:00:11Z","updated_at":"2026-05-14T16:01:08Z"}]}
```

按 `created_at -> updated_at` 粗略计算，本轮单任务完成耗时约 `57s`。

## 9. 结果汇总

| 验证项 | 预期 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| `GET /health` | API 可用并返回 DB / task points 信息 | 返回 `status=ok` | 通过 |
| `POST /tasks` | 能创建 `pending` task | `station_a` 创建成功 | 通过 |
| executor HTTP intake | 能通过 HTTP 获取最早一条 `pending` task | `task_id=1` 被成功消费 | 通过 |
| Nav2 ready gate | ready 后才允许执行 | 5 个 lifecycle active，TF 和 action server 可用 | 通过 |
| `NavigateToPose` | 成功发送并完成目标 | `Goal succeeded` | 通过 |
| HTTP 状态回写 | 最终状态可被 HTTP 查询到 | `status=succeeded`，`status_reason` 已写回 | 通过 |

## 10. 结论与边界

本轮已经证明，当前主线可以被准确描述为：

“在 Gazebo + Nav2 仿真环境中，Mock WMS 通过 HTTP 创建任务，executor 消费任务后接回 Nav2 执行，并把最终状态通过 HTTP 查询链路回写出来的最小闭环验证系统。”

同时仍需保持以下口径：

- 这不是完整 WMS
- 这不是多机器人调度系统
- 这不是生产级后端
- 这是一条面向物流机器人任务执行、导航验证、测试验收的最小可复核闭环
