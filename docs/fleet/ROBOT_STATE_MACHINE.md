# Robot State Machine

日期：`2026-08-17`  
范围：Stage 1 Robot Registry。本文件描述 Fleet 层机器人状态，不描述 WMS 任务状态或 Nav2 执行细节。

## 1. 机器人记录

每台机器人至少包含：

| 字段 | 含义 |
| --- | --- |
| `robot_id` | 唯一标识，例如 `robot_01` |
| `state` | 当前 Fleet 机器人状态 |
| `current_task_id` | 当前绑定的任务 ID；无任务时为 `null` |
| `current_station` | 站点抽象，例如 `start_zone`、`station_a` |
| `last_heartbeat` | 最近一次心跳时间（UTC ISO8601） |
| `battery` | 模拟电量百分比 |

默认种子：

```text
robot_01 @ start_zone
robot_02 @ start_zone
```

实现入口：

- `amr_warehouse_sim/fleet/registry.py`
- 可选 SQLite：`data/fleet.db` 表 `robots`

## 2. 状态集合

```text
IDLE
ASSIGNED
BUSY
OFFLINE
ERROR
```

含义：

| 状态 | 含义 |
| --- | --- |
| `IDLE` | 在线、无 active task，可被调度 |
| `ASSIGNED` | 已绑定任务，尚未进入关键执行 |
| `BUSY` | 正在执行任务（导航或模拟 pickup/dropoff） |
| `OFFLINE` | 心跳超时或失联，不可接任务 |
| `ERROR` | 机器人级故障，需人工或上层恢复 |

## 3. 合法状态转移

```text
IDLE
  -> ASSIGNED | OFFLINE | ERROR

ASSIGNED
  -> BUSY | IDLE | OFFLINE | ERROR

BUSY
  -> IDLE | OFFLINE | ERROR

OFFLINE
  -> IDLE | ERROR

ERROR
  -> IDLE | OFFLINE
```

说明：

- `assign_task()`：`IDLE -> ASSIGNED`，写入 `current_task_id`
- `mark_busy()`：`ASSIGNED -> BUSY`
- `release_task()`：`ASSIGNED | BUSY -> IDLE`，清空 `current_task_id`
- `mark_offline()`：任意非 OFFLINE 状态 -> `OFFLINE`
- `record_heartbeat()`：若机器人为 `OFFLINE` 且仍无 active task，可恢复为 `IDLE`

## 4. 关键约束

1. **同一 robot 不能同时拥有两个 active task**  
   `current_task_id != null` 且状态为 `ASSIGNED` 或 `BUSY` 时，拒绝再次 `assign_task()`。

2. **OFFLINE robot 不能接任务**  
   `assign_task()` 与 `can_accept_task()` 都会拒绝。

3. **Fleet 状态与 WMS 任务状态分离**  
   `tasks.status` 仍表示 Mock WMS 业务任务；机器人状态只存在于 Fleet registry。

4. **数据结构不与 GUI 耦合**  
   Registry 返回 `RobotRecord` / `dict`，供后续 FastAPI 和 Dispatcher 复用。

## 5. SimulatedRobotContext

Stage 1 不启动第二套 Nav2。调度层验证使用：

```text
SimulatedRobotContext(robot_id, registry)
  -> check_ready_gate()
  -> navigate_to_pose()
  -> complete_assigned_task()
```

这对应未来 per-robot `RobotExecutionContext` 的测试替身，不等同于真实 Nav2 执行。

## 6. 与后续 Stage 的关系

| 后续 Stage | 如何使用本状态机 |
| --- | --- |
| Stage 2 Dispatcher | 只从 `IDLE + heartbeat valid + no active task` 中选车 |
| Stage 3 搬运 FSM | WMS / assignment / robot execution 三套状态分开演进 |
| Stage 4 Heartbeat | 超时后将 robot 置 `OFFLINE`，并触发任务重分配 |
| Stage 6 多机器人 Nav2 | 每个 `robot_id` 对应独立 execution context，而不是复制 WMS |

## 7. 当前未覆盖

- 真实 Nav2 ready gate 绑定到 `robot_id`
- 心跳 sweep 后台任务
- FastAPI `/robots` 路由
- 生产级 recovery 语义

这些属于 Stage 2 及以后，不属于 Stage 1 范围。
