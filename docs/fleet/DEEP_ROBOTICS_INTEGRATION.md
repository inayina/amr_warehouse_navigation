# DR02 Pro ROS 2 Vendor Integration

审计与实现日期：`2026-08-23`

状态：**experimental / opt-in / state-only**。当前代码、无 vendor 依赖测试，以及官方 DR02 Pro MuJoCo `/JOINTS_DATA` → adapter → SQLite heartbeat runtime 已验证；未做 SDK command、task execution 或真机验证。

## 1. Motivation

本实验验证一个窄而真实的边界：

```text
第三方机器人 ROS 2 SDK / simulator
              ↓
vendor message + DDS
              ↓
vendor adapter
              ↓
内部 Fleet RobotRegistry
```

它不是完整异构 Fleet：没有 DR02 localization、map contract、Nav2 controller、`NavigateToPose → DR02`、capability dispatch 或 warehouse task execution。也没有发送任何运动命令。

## 2. Existing architecture

```text
Mock WMS
    ↓
FleetDispatcher
    ↓
HaulTaskController
    ↓
RobotExecutionContext (Protocol)
    ↓
SimulatedRobotContext (default fallback)
```

`RobotExecutionContext` 只描述 haul controller 当前真正消费的 `check_ready_gate()` 与 `navigate_to_pose()` contract。原来的 `SimulatedRobotContext` 仍是默认实现，所以 Stage 1–5 的测试行为不变。这里仅创建 execution seam，不提供 DR02 execution context。

## 3. Vendor architecture

```text
DR02 Pro MuJoCo
      ↓ publish
ROS 2 / DDS
      ↓
drdds/msg/Joints on /JOINTS_DATA
      ↓ subscribe
DeepRoboticsStateAdapter
      ↓ record_heartbeat(recover_offline=False)
RobotRegistry
      ↓
robot_02.last_heartbeat
```

一帧类型正确的 `/JOINTS_DATA` 只证明 vendor ROS 2 / DDS telemetry path 存活。adapter 不修改 `state`、`current_task_id`、`current_station` 或 `battery`，也不推断 pose、任务完成或执行能力。

## 4. rclcpp vs rclpy

官方 DR02 Pro SDK 是 C++ ROS 2 package，使用 `rclcpp`。当前官方 `RobotInterface` 接收一个 `rclcpp::Node::SharedPtr`，通过 node 创建：

- `/JOINTS_CMD` 的 `rclcpp::Publisher<drdds::msg::JointsCmd>`；
- `/JOINTS_DATA` 的 `rclcpp::Subscription<drdds::msg::Joints>`；
- 绑定到 `HandleJointData` 的 callback；
- depth 为 `10` 的 QoS shorthand；等待首帧时调用 `rclcpp::spin_some(node_)`。

本仓 adapter 是 Python/`rclpy` subscriber，同样订阅 `drdds/msg/Joints`，depth 为 `10`。两端不共享 C++ class 或 Python object；它们共享的是 topic name、ROS message type 与 QoS compatibility。ROS 2 使用 DDS 完成 discovery、序列化和跨进程 transport，所以 C++ publisher 可以和 Python subscriber 通信。

## 5. SDK、message package、simulator 与 MuJoCo

| 组件 | 当前职责 |
| --- | --- |
| [`deep-robotics-sdk2`](https://github.com/DeepRoboticsLab/deep-robotics-sdk2) | C++/`rclcpp` 产品 SDK package、状态机和 topic examples；DR02 Pro ROS package 名为 `dr02_pro`。 |
| [`deep-robotics-msg`](https://github.com/DeepRoboticsLab/deep-robotics-msg) | ROS 2 `msg/`、`srv/` interface definitions；构建后 package 名为 `drdds`，为 C++/Python 生成语言 binding。 |
| [`deep-robotics-simulation`](https://github.com/DeepRoboticsLab/deep-robotics-simulation) | Python 启动和维护的 DEEPRobotics product simulation；DR02 Pro 入口为 `python3 run_sim.py dr02_pro`。 |
| MuJoCo | DR02 Pro 的 physics backend；不是 Gazebo，也不需要移植进本仓 warehouse world。 |

SDK header 是 C++ 编译期接口，例如 `drdds/msg/joints.hpp` 与 `rclcpp/rclcpp.hpp`。Python adapter 不 include 这些 header，而是加载同一 ROS interface 生成的 `drdds.msg.Joints` Python type。

## 6. 官方当前 source audit

事实源为三个官方仓库 `main` 分支，审计日期 `2026-08-23`。runtime 使用的临时 shallow checkout SHA 为：

- `deep-robotics-msg`: `aa646c1782aa982f384b7e46469723f31696f778`
- `deep-robotics-sdk2`: `5b5a8a82911750678d1e94fed257eebbe33f5062`
- `deep-robotics-simulation`: `3e848b3b9bb725521bb1f70a3d1a2913a8d70e92`

审计入口：

- SDK 总览与 DR02 Pro guide：[`deep-robotics-sdk2/src/dr02_pro`](https://github.com/DeepRoboticsLab/deep-robotics-sdk2/tree/main/src/dr02_pro)
- 仿真支持矩阵：[`SIMULATION_CN.md`](https://github.com/DeepRoboticsLab/deep-robotics-sdk2/blob/main/src/dr02_pro/docs/SIMULATION_CN.md)
- Topic 示例矩阵：[`EXAMPLES_CN.md`](https://github.com/DeepRoboticsLab/deep-robotics-sdk2/blob/main/src/dr02_pro/docs/EXAMPLES_CN.md)
- C++ topic/callback 实现：[`robot_interface.hpp`](https://github.com/DeepRoboticsLab/deep-robotics-sdk2/blob/main/src/dr02_pro/state_machine/interface/robot_interface.hpp)
- DR02 Pro simulator topics：[`deep-robotics-simulation/dr02_pro/README_CN.md`](https://github.com/DeepRoboticsLab/deep-robotics-simulation/blob/main/dr02_pro/README_CN.md)
- message package：[`deep-robotics-msg`](https://github.com/DeepRoboticsLab/deep-robotics-msg)

| Item | Finding |
| --- | --- |
| SDK language | C++ |
| ROS client | `rclcpp`; Node/Publisher/Subscription/callback/`spin_some` 均在当前源码可见 |
| Message package | `deep-robotics-msg`，ROS package 名 `drdds` |
| DDS / ROS 2 role | discovery、message serialization 与跨进程 transport；双方仍须 topic/type/QoS/domain compatible |
| Simulation backend | MuJoCo；官方入口 `python3 run_sim.py dr02_pro` |
| `/JOINTS_DATA` | `drdds/msg/Joints`；simulator → SDK/adapter；官方低层仿真支持 |
| `/JOINTS_CMD` | `drdds/msg/JointsCmd`；SDK → simulator；官方低层仿真支持，但本实验不发布 |
| High-level simulation support | `/MOTION_INFO`、`/MOTION_STATE`、`/GAIT`、`/STEER`、`/REAL_STEER` 当前均标为不支持仿真 |
| ROS_DOMAIN_ID | simulator、SDK、adapter/诊断终端必须一致；值本身只用于隔离 ROS domain |

官方 simulator 还说明 DR02 Pro SDK 定义 31 个关节、MuJoCo 模型有 29 个 actuator，最后两个 SDK joint 在 state publication 中填零。这是 message/simulator mapping 事实，不是 Fleet capability。

## 7. Data flow 与 callback

```text
MuJoCo simulation step
→ simulator ROS publisher
→ DDS writer / discovery / serialization
→ /JOINTS_DATA
→ rclpy subscription queue
→ executor spin dispatches callback
→ DeepRoboticsStateAdapter.on_vendor_telemetry_received()
→ RobotRegistry.record_heartbeat(recover_offline=False)
→ in-memory RobotRecord + optional SQLite upsert
```

callback 是 subscriber 收到可交付 message 后由 ROS executor 调用的函数。只创建 subscription 而不 `spin()`，callback 不会执行。

## 8. Dependency boundary

`drdds` 是 opt-in runtime dependency，不写入本包的 mandatory `package.xml` dependency，也不会在 `amr_warehouse_sim` 或 `fleet` 顶层 import。ROS wrapper 只在实际启动时 lazy-load `rclpy` 与 `drdds.msg.Joints`。

缺少 `drdds` 时 standalone command fail-fast：

```text
Deep Robotics integration requires the ROS 2 package `drdds`.
Install/source DeepRoboticsLab/deep-robotics-msg before running this optional integration.
```

因此原有 AMR、Gazebo、Nav2、Mock WMS 与 Fleet pytest 不需要安装 SDK、message package 或 simulator。

## 9. Embedded 与 standalone

同进程 mapping：

```python
adapter = DeepRoboticsStateAdapter(registry=registry, robot_id='robot_02')
# ROS callback 收到一帧后：
adapter.on_vendor_telemetry_received()
```

standalone ROS node：

```bash
export ROS_DOMAIN_ID=10
source /opt/ros/jazzy/setup.bash
source /path/to/deep-robotics-msg/install/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 run amr_warehouse_sim deep_robotics_state_adapter \
  --robot-id robot_02 \
  --fleet-db ~/ros2_ws/src/amr_warehouse_sim/data/fleet.db
```

同进程模式更新同一个 `RobotRegistry` object。两个 Python process 不共享内存；standalone 模式只把 heartbeat upsert 到 SQLite。已运行的另一个 Fleet process 不会自动刷新它先前载入的 in-memory registry，因为当前没有常驻 Fleet service、database watcher 或跨进程 event bus。

## 10. ROS 2 runtime 练习步骤

以官方当前文档为准准备 `deep-robotics-msg` 与 `deep-robotics-simulation`，所有终端使用相同 ROS distro、message overlay 与 `ROS_DOMAIN_ID`。

Simulator terminal：

```bash
export ROS_DOMAIN_ID=10
source /opt/ros/jazzy/setup.bash
source /path/to/deep-robotics-msg/install/setup.bash
source /path/to/deep-robotics-simulation/.venv/bin/activate
python3 run_sim.py dr02_pro
```

Diagnostic terminal：

```bash
ros2 node list
ros2 topic list
ros2 topic info /JOINTS_DATA --verbose
ros2 topic hz /JOINTS_DATA
ros2 topic echo /JOINTS_DATA --once
ros2 interface show drdds/msg/Joints
```

Adapter terminal：按第 9 节启动，再核对 subscriber count 与 SQLite 中 `robot_02.last_heartbeat` 前后值。本实验不运行 `/JOINTS_CMD` publisher。

## 11. Troubleshooting tree

### `/JOINTS_DATA` 不存在

1. simulator process 是否仍在运行，启动参数是否为 `dr02_pro`；
2. terminal 是否 source 正确 ROS distro；
3. `ros2 pkg prefix drdds` 与 `ros2 interface show drdds/msg/Joints` 是否成功；
4. simulator、adapter、diagnostic terminal 的 `ROS_DOMAIN_ID` 是否一致；
5. DDS discovery 是否被容器、host networking、firewall、interface selection 或不同 RMW implementation 阻断。

### topic 存在但 publisher count 为 0

检查 simulator process/log、product config、ROS node 是否还活着；topic name 残留在某个工具输出中不等于当前有 writer。

### publisher 存在但 adapter callback 不触发

检查 `ros2 topic info /JOINTS_DATA --verbose` 中 type 和 QoS；确认 type 为 `drdds/msg/Joints`、domain 一致、subscriber 已创建且进程正在 `rclpy.spin(node)`。若 QoS 不 compatible，discovery 可见也不会交付 message。

### callback 触发但 Registry 不更新

检查 adapter log 的 receive count、`robot_id` 是否存在、所用 registry object/`--fleet-db` 是否是预期实例与路径、SQLite 是否可写，以及 callback exception。

### 不同 terminal 看不到彼此

逐个打印 `ROS_DISTRO`、`ROS_DOMAIN_ID`、`RMW_IMPLEMENTATION` 与 overlay 路径；确认使用同一 `drdds` interface version。重新 source 只改变当前 shell，不会改变已经启动的 process。

## 12. Evidence matrix

| Capability | Code | Unit Test | ROS Runtime | Simulation | Real Robot |
| --- | --- | --- | --- | --- | --- |
| Execution context abstraction | PASS | PASS | N/A | N/A | N/A |
| DR02 telemetry → heartbeat mapping | PASS | PASS | PASS | PASS (MuJoCo) | NOT TESTED |
| Optional dependency fail-fast | PASS | PASS | PASS | N/A | N/A |
| DR02 task execution | NOT IMPLEMENTED | — | — | — | — |
| DR02 `NavigateToPose` | NOT IMPLEMENTED | — | — | — | — |
| DR02 command publication | NOT IMPLEMENTED | — | — | — | — |

### 12.1 本机 runtime evidence

| Item | Measured result |
| --- | --- |
| ROS distro | Jazzy |
| `ROS_DOMAIN_ID` | `42` |
| Simulator command | `python3 run_sim.py dr02_pro` |
| Headless adjustment | 仅将临时 checkout 的 `viewer.enabled` 从 `true` 改为 `false` |
| Simulator node | `/dr02_pro_simulation` |
| `/JOINTS_DATA` type | `drdds/msg/Joints` |
| Publisher / subscriber count | `1 / 1` |
| Endpoint QoS | publisher 与 subscriber 均为 `RELIABLE / VOLATILE` |
| Measured Hz | 6 秒短窗口最终 average `285.067 Hz`；官方 config target 为 `500 Hz`，两者不混写 |
| One-frame inspection | `header + 31 JointValue`；本次静止 whole-mode frame 的 position/torque/velocity 为 0 |
| Adapter final clean run | 首帧 callback 成功；Ctrl+C 前累计 `3209` frames；exit code `0` |
| `robot_02` before | `OFFLINE`, heartbeat `2026-08-23T00:00:00Z`, station `start_zone`, battery `100.0` |
| `robot_02` after | `OFFLINE`, heartbeat `2026-08-23T08:21:42Z`, station `start_zone`, battery `100.0` |

说明：这个 `PASS` 只覆盖官方 MuJoCo telemetry 到本仓 Registry persistence。它不覆盖 SDK state machine、`/JOINTS_CMD`、高层 motion topics、warehouse execution 或真机。首次 sandbox 内运行曾被 DDS socket 权限阻塞；在允许本地 DDS socket 后完成验证。首次 adapter Ctrl+C 还暴露了默认 rclpy signal handler 与高频 callback 的 shutdown race，最终使用 `SignalHandlerOptions.NO` 让主进程统一处理 `KeyboardInterrupt` 和幂等 shutdown，复测干净退出。

## 13. Future work（不属于本轮）

- 在真实需求出现后定义 `robot_type/vendor/capabilities/executor_type`，再讨论 schema migration；
- 只有建立 DR02 localization、map、controller 与 safety contract 后，才能讨论 task execution；
- capability-aware dispatch、inspection workflow、常驻 Fleet service 与跨进程 refresh 各自需要独立设计和验收；
- 上真机前必须重新核对官方 Developer Mode、安全和单一 `/JOINTS_CMD` publisher 约束。
