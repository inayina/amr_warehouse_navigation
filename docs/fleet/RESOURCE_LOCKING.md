# Resource Locking

日期：`2026-08-17`  
范围：Stage 5 最小逻辑资源占用。这不是完整交通管制，也不是 collision-free multi-agent planning。

## 1. 为什么需要 resource ownership

多台 AMR 共享仓库时，有些区域不能同时被占用，例如：

- 某个 pickup 站点前的接近区
- 某段窄通道

Nav2 只能做**单车**避障，不会替 Fleet 决定“这条窄通道现在归谁”。  
EMS 因此需要一层很薄的 **logical resource lock**：

```text
FREE
  → OWNED(robot_id)
  → release / timeout
  → FREE or next waiter
```

## 2. 第一版资源

默认 demo 资源：

| resource_id | 含义 |
| --- | --- |
| `pickup_station_a` | station_a 取货逻辑区 |
| `narrow_aisle_1` | 仓库窄通道占位 |

实现：`ResourceLockManager`（`amr_warehouse_sim/fleet/resources.py`）

## 3. 基本操作

```python
manager = ResourceLockManager()

manager.acquire('narrow_aisle_1', 'robot_01')   # acquired
manager.acquire('narrow_aisle_1', 'robot_02')   # waiting

manager.release('narrow_aisle_1', 'robot_01')   # robot_02 may acquire
```

结果枚举：

- `acquired`：立即获得 ownership
- `waiting`：进入 FIFO 等待队列
- `already_owned`：同一 robot 重复 acquire

事件：

```text
RESOURCE_ACQUIRED
RESOURCE_WAITING
RESOURCE_RELEASED
RESOURCE_TIMEOUT
```

## 4. 等待与释放

```text
Robot_01 owns narrow_aisle_1
Robot_02 acquire -> WAITING
Robot_01 release
Robot_02 acquire -> ACQUIRED
```

等待队列按 FIFO 处理。释放后自动尝试授予队首 robot。

## 5. Timeout

若 ownership 超过 `ownership_timeout_sec`（默认 120s），`sweep_timeouts()` 会：

1. 强制 release 当前 owner
2. 发出 `RESOURCE_TIMEOUT`
3. 尝试把资源授予下一个 waiter

这是 demo 级兜底，不是生产交管策略。

## 6. 防死锁：lock ordering

若一次需要多个资源，必须按 **resource_id 字典序** 申请：

```python
manager.acquire_ordered('robot_01', ['narrow_aisle_1', 'pickup_station_a'])
```

规则：所有 robot 使用相同排序，避免：

```text
robot_01 持有 A，等 B
robot_02 持有 B，等 A
```

本 demo **没有** 实现：

- collision-free multi-agent planning
- production traffic control
- deadlock-free fleet management（除 lock ordering 外）

## 7. 与 Nav2 / EMS 的边界

- Resource lock **不发** `/cmd_vel`
- Resource lock **不做** 路径规划
- Nav2 仍负责局部避障；Fleet lock 只表达“能不能进入某逻辑区”
- 当前未把 resource acquire 自动挂到 `HaulTaskController`；后续可按站点 / 通道规则接入

## 8. 当前未覆盖

- 与 Gazebo / Nav2 的真实 zone 触发
- 动态资源地图
- 优先级抢占
- 可视化占用面板
