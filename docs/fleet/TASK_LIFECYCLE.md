# Task Lifecycle

日期：`2026-08-17`  
范围：Stage 3 最小搬运任务。本文件把 **WMS 任务状态**、**Fleet assignment 状态** 和 **Robot execution 状态** 分开说明。它们不是同一个字段。

## 1. 为什么要拆三套状态

单点 Mock WMS 只用 `tasks.status = pending / running / succeeded / failed / canceled`。  
一台车、一个 goal 时，这够用。

搬运任务不行：

- WMS 只应关心“这单货有没有完成”
- Fleet 只应关心“这单现在绑在哪台车上”
- 机器人只应关心“我正在去取货、正在取货、还是正在送货”

如果把 `NAVIGATING_TO_PICKUP` 写进 WMS `tasks.status`，Dashboard 和 CLI 都会把执行细节当成业务终态。

## 2. 三套状态

### 2.1 WMS task state（业务）

```text
PENDING
  → ASSIGNED
  → IN_PROGRESS
  → SUCCEEDED | FAILED | CANCELED | REQUEUED

REQUEUED
  → ASSIGNED | CANCELED
```

实现：`WmsTaskStatus`（`amr_warehouse_sim/fleet/task_lifecycle.py`）

与现有 Mock WMS 粗粒度字段的映射（不改 `tasks` 表枚举）：

| Fleet WMS status | 现有 `tasks.status` |
| --- | --- |
| `pending` | `pending` |
| `assigned` / `in_progress` | `running` |
| `succeeded` | `succeeded` |
| `failed` | `failed` |
| `canceled` | `canceled` |
| `requeued` | `pending` |

### 2.2 Fleet assignment state（调度绑定）

```text
assigned → executing → completed
                      → failed
                      → canceled
                      → released
```

实现：`AssignmentStatus`。`released` 表示任务已从当前机器人解绑，可供 Stage 4 重分配。

### 2.3 Robot execution state

机器人级（Registry）：

```text
IDLE | ASSIGNED | BUSY | OFFLINE | ERROR
```

搬运子阶段（Haul execution phase）：

```text
IDLE
  → NAVIGATING_TO_PICKUP
  → PICKUP                 # 第一版：ack / 状态转移，不接真实机构
  → NAVIGATING_TO_DROPOFF
  → DROPOFF                # 第一版：ack / 状态转移
  → SUCCEEDED

异常：FAILED | CANCELED | REQUEUED
```

`REQUEUED` 只允许在 **pickup 尚未完成** 时发生。Pickup 完成后视为 demo 级不可逆（货物已在车上）。

## 3. 成功路径

```text
WMS:        PENDING → ASSIGNED → IN_PROGRESS --------------------→ SUCCEEDED
Assignment:           assigned → executing ----------------------→ completed
Robot:                ASSIGNED → BUSY ---------------------------→ IDLE
Execution:            idle → nav_pickup → pickup → nav_dropoff → dropoff → succeeded
```

入口：

```python
controller = HaulTaskController(
    task_id=1,
    pickup_station='station_a',
    dropoff_station='station_b',
    dispatcher=dispatcher,
)
controller.run_simulated_success(now=...)
```

PICKUP / DROPOFF 第一版不 sleep、不接机械结构，只做 acknowledgement 状态转移。

## 4. 异常

| 动作 | WMS | Assignment | Execution | Robot |
| --- | --- | --- | --- | --- |
| 导航失败（取货前） | `failed` | `failed` | `failed` | 释放回 `IDLE` |
| cancel（取货前） | `canceled` | `canceled` | `canceled` | 释放回 `IDLE` |
| requeue（取货前） | `requeued` | `released` | `requeued` | 释放回 `IDLE`，清 `robot_id` |
| requeue / cancel（取货后） | 拒绝 | 不变 | 不变 | 不变 |

Stage 4 会在 heartbeat timeout 时调用这条 requeue 路径。  
**demo-level reassignment ≠ production recovery semantics。**

## 5. 与单车 baseline 的关系

- `mock_wms_executor` 仍执行单点 `target_name` NavigateToPose，行为不变。
- `DispatchTask(pickup_station=...)` 仍可只做 Stage 2 分配，不进入 haul FSM。
- Haul FSM 需要显式 `dropoff_station`，由 `HaulTaskController` 驱动。
- 不修改 `navigation.launch.py` / `nav2_params.yaml`。
- 导航仍通过 `SimulatedRobotContext` 验证；真实 Nav2 仍走现有单车 executor。

## 6. 当前未覆盖

- 把 haul 字段写回 Mock WMS SQLite `tasks` 表
- FastAPI 创建 pickup/dropoff 任务
- 真实 NavigateToPose 两段执行
- FastAPI `POST /robots/{robot_id}/heartbeat`

## 7. Heartbeat / Offline / Reassignment（Stage 4）

入口：`HeartbeatMonitor.sweep()` + `reassign_requeued()`。

```text
robot last_heartbeat timeout
  → HEARTBEAT_TIMEOUT
  → 若任务尚未完成 PICKUP：
        release assignment
        WMS → REQUEUED
        robot → OFFLINE
        dispatcher → 另一台 IDLE 机器人
        TASK_REASSIGNED
  → 若任务已经完成 PICKUP：
        robot → OFFLINE
        任务保持绑定，不重分配
```

**demo-level reassignment ≠ production recovery semantics.**

本 demo 只覆盖“分配后、取货前失联”。生产系统还要处理：货物是否已在车上、Nav2 goal 是否已发出、站点占用、人工接管、充电锁定等。取货后失联在这里故意不假装已经恢复。
