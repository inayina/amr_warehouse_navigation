# Fleet / EMS 文档索引

日期：`2026-08-23`

本目录描述在原有 **单机器人 Mock WMS → Nav2** 闭环之上，新增的最小 Fleet / EMS 调度学习层。

**口径：** 这是 demo / 学习用途的最小调度抽象，**不是**生产级 WMS、交通管制或多机协同平台。

## 推荐阅读顺序

1. [EMS_FLEET_ARCHITECTURE_AUDIT.md](./EMS_FLEET_ARCHITECTURE_AUDIT.md)  
   Stage 0 只读审计：为何需要 EMS 层、当前缺口、分阶段计划。
2. [EMS_FLEET_DESIGN.md](./EMS_FLEET_DESIGN.md)  
   WMS / Fleet / Robot Executor / Nav2 职责边界与组件映射（Stage 1–5 已落地）。
3. [ROBOT_STATE_MACHINE.md](./ROBOT_STATE_MACHINE.md)  
   Robot Registry：`IDLE / ASSIGNED / BUSY / OFFLINE / ERROR`。
4. [TASK_LIFECYCLE.md](./TASK_LIFECYCLE.md)  
   WMS 任务、Fleet assignment、Robot execution 三套状态分离。
5. [RESOURCE_LOCKING.md](./RESOURCE_LOCKING.md)  
   逻辑资源占用：acquire / release / timeout / lock ordering。
6. [MULTI_ROBOT_DEMO.md](./MULTI_ROBOT_DEMO.md)  
   Stage 6 未实施：Gazebo / Nav2 双车 blocker 与 opt-in 迁移计划。
7. [DEEP_ROBOTICS_INTEGRATION.md](./DEEP_ROBOTICS_INTEGRATION.md)

   Experimental、opt-in、state-only 的 DR02 Pro ROS 2 telemetry → Fleet heartbeat 实验；不是 DR02 task execution。
8. [UNITREE_INTEGRATION.md](./UNITREE_INTEGRATION.md)

   Experimental、opt-in、state-only 的 Unitree Go2 CycloneDDS / ROS 2 telemetry → Fleet heartbeat 实验；Jazzy runtime 未验证。
9. [AGIBOT_INTEGRATION.md](./AGIBOT_INTEGRATION.md)

   Experimental D1 MaxPro C++ SDK probe → JSONL process boundary → Fleet heartbeat；没有真机或控制证据。
10. [VENDOR_INTEGRATION_COMPARISON.md](./VENDOR_INTEGRATION_COMPARISON.md)

    对比 DR02、Unitree、Agibot 三种外部 architecture，以及真正稳定的 internal liveness contract。

## 阶段状态

| Stage | 内容 | 状态 |
| --- | --- | --- |
| 0 | 架构审计 | ✅ |
| 1 | Robot Registry | ✅ |
| 2 | Fleet Dispatcher | ✅ |
| 3 | Pickup → Dropoff Haul FSM | ✅ |
| 4 | Heartbeat / Reassignment | ✅ |
| 5 | Resource Lock | ✅ |
| 6 | Multi-Robot Gazebo / Nav2 | ❌ 有意 deferred |
| 7 | 文档 / README 收口 | ✅ |
| DR02 vendor experiment | `/JOINTS_DATA` → Registry heartbeat | Code / unit / MuJoCo ROS runtime verified；真机未测试 |
| Unitree vendor experiment | `/lowstate` → Registry heartbeat | Code / unit verified；Jazzy runtime 未验证 |
| Agibot vendor experiment | C++ SDK probe JSONL → Registry heartbeat | SDK/probe compile-link + mock IPC + unit verified；真机未测试 |

## 代码入口

```python
from amr_warehouse_sim.fleet import (
    RobotRegistry,
    FleetDispatcher,
    HaulTaskController,
    HeartbeatMonitor,
    ResourceLockManager,
)
```

实现目录：`amr_warehouse_sim/fleet/`

可选 SQLite：`data/fleet.db`（运行时生成，不入库）

## 测试入口

```bash
python3 -m pytest test/integration/test_fleet_*.py -q
python3 -m pytest test -q   # 含 Scenario H 单车 baseline 回归
```

| 测试文件 | 场景 |
| --- | --- |
| `test_fleet_registry.py` | Registry 状态机 |
| `test_fleet_dispatcher.py` | Scenarios A–D 分配 |
| `test_fleet_haul_lifecycle.py` | 搬运 FSM |
| `test_fleet_heartbeat.py` | Scenario E 重分配 |
| `test_fleet_resource_lock.py` | Scenarios F/G 资源锁 |
| `test_fleet_execution_context.py` | vendor-neutral execution seam |
| `test_deep_robotics_state_adapter.py` | vendor telemetry mapping / optional dependency |
| `test_unitree_state_adapter.py` | Unitree LowState mapping / optional dependency / DR02 parity |
| `test_agibot_state_adapter.py` | Agibot JSONL process contract / lifecycle / three-vendor parity |

## 与单车 baseline 的关系

- `mock_wms_executor` / `mock_wms_task_runner` 仍可独立运行。
- Fleet 层是 **opt-in** 增量；未接 Dispatcher 时不改变 V3 行为。
- `navigation.launch.py` 与 `config/nav2_params.yaml` 仍冻结为 V2 稳定基线。
