# EMS Fleet Design

日期：`2026-08-17`  
范围：Stage 1–5 已落地；Stage 6（Gazebo / Nav2 双车）有意 deferred。本文件说明 WMS / Fleet / Robot Executor / Nav2 的职责边界，并把本仓库组件映射进去。文档索引见 [README.md](./README.md)。

## 1. 工业分层

```text
WMS
  有什么业务任务需要完成

EMS / Fleet Dispatcher
  哪台机器人去做、分配成本、跟踪 assignment

Robot Executor
  已分配任务 -> NavigateToPose -> 执行结果

Nav2
  全局规划、局部控制、行为树
```

原则：

- Mock WMS **不**决定哪台机器人执行。
- Fleet Dispatcher **不**发 `/cmd_vel`，**不**做路径规划。
- Robot Executor **不**改 Nav2 参数，只消费 assigned task。
- Nav2 **不**维护 fleet 心跳或任务队列。

## 2. 本仓库组件映射

| 工业角色 | 当前实现 | Stage |
| --- | --- | --- |
| WMS | `mock_wms_db_common.py`、`mock_wms_api.py`、CLI create/list | V3 |
| EMS / Fleet | `registry.py`、`dispatcher.py`、`haul_executor.py`、`heartbeat.py`、`resources.py` | Stage 1–5 |
| Robot Executor | `mock_wms_executor.py`（单车）；未来 per-robot context | V3 / 后续 |
| Nav2 | `navigation.launch.py`、`nav2_params.yaml` | V2 |
| AMR | Gazebo `my_robot` | V1–V2 |

## 3. 数据边界

### WMS Task（`data/mock_wms.db` → `tasks`）

表示业务任务意图。

- V3 Mock WMS `tasks` 表仍是单点 `target_name` + `pending/running/succeeded/failed/canceled`。
- Stage 3 搬运业务状态在 Fleet 层：`WmsTaskStatus`（`pending / assigned / in_progress / succeeded / failed / canceled / requeued`）。
- 粗粒度映射见 `docs/fleet/TASK_LIFECYCLE.md`。本轮不改 Mock WMS 表枚举，避免单车 baseline 回归。

### Robot（`data/fleet.db` → `robots`）

表示机器人运行时注册信息：

```text
robot_id, state, current_task_id, current_station, last_heartbeat, battery
```

### Assignment（`data/fleet.db` → `assignments`）

表示 Fleet 调度结果，与 WMS `tasks.status` 分开：

```text
task_id, robot_id, pickup_station, cost, dispatch_reason, status, assigned_at
status ∈ assigned | executing | completed | failed | canceled | released
```

同一 `task_id` 在 assignment 层唯一，避免重复 active assignment。

## 4. Stage 2 Dispatcher

### 候选机器人

```text
state == IDLE
AND heartbeat valid
AND no active task
```

对应 `RobotRegistry.can_accept_task()`。

### 第一版 cost

```text
cost = distance_to_pickup
     + workload_penalty
     + optional_priority_penalty
```

- `distance_to_pickup`：用 `config/task_points.yaml` 中 `current_station -> pickup_station` 的静态欧氏距离。
- `workload_penalty`：Stage 2 默认 `0`。
- `priority_penalty`：`high` 优先级任务减 `0.5`，用于同距离时的轻微优先，不是完整 SLA 模型。

选择规则：cost 最小者优先；平局时按 `robot_id` 字典序。

### 入口

```python
dispatcher = FleetDispatcher(registry, task_points_path=...)
assignment = dispatcher.assign_task(
    DispatchTask(task_id=1, pickup_station='station_a'),
    now=...,
)
```

批量：

```python
dispatcher.dispatch_tasks([task_a, task_b], now=...)
```

### 事件

分配成功时输出结构化事件：

```json
{"timestamp": "...", "event": "TASK_ASSIGNED", "task_id": 1, "robot_id": "robot_01", "reason": "..."}
```

## 5. Stage 3 搬运 FSM

入口：`HaulTaskController`。需要 `pickup_station` 和 `dropoff_station`。

三套状态必须同时存在、互不覆盖，详见 `docs/fleet/TASK_LIFECYCLE.md`。

PICKUP / DROPOFF 第一版是 acknowledgement，不接真实机构，也不 `sleep`。

## 6. Stage 4 Heartbeat / Reassignment

入口：`HeartbeatMonitor`。

- 超时：`HEARTBEAT_TIMEOUT` → `ROBOT_OFFLINE`
- 取货前：任务 `REQUEUED`，再 `TASK_REASSIGNED`
- 取货后：不重分配

> demo-level reassignment ≠ production recovery semantics

## 7. Stage 5 Resource Lock

入口：`ResourceLockManager`。

- 状态：`FREE` / `OWNED(robot_id)`
- 操作：`acquire` / `release` / `sweep_timeouts`
- 冲突：第二个 robot `WAITING`
- 防死锁：多资源按 `resource_id` 字典序 acquire

详见 `docs/fleet/RESOURCE_LOCKING.md`。这不是完整 traffic management。

## 8. 当前未做

- WMS 与 Dispatcher 的自动轮询闭环
- FastAPI `/robots`、`/fleet/assignments`
- 把 pickup/dropoff 写回 Mock WMS SQLite 表
- Resource lock 接入 `HaulTaskController` 执行路径
- 真实双 Nav2 / Gazebo 双车（Stage 6，见 [MULTI_ROBOT_DEMO.md](./MULTI_ROBOT_DEMO.md)）

## 9. 与单车 baseline 的关系

- 现有 `mock_wms_executor` / `mock_wms_task_runner` 仍可独立运行。
- Fleet 层是 opt-in 增量；未接 Dispatcher 时不改变 V3 行为。
- `navigation.launch.py` 与 `nav2_params.yaml` 仍冻结。
