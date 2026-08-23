# Unitree Go2 ROS 2 Vendor Integration

审计与实现日期：`2026-08-23`

状态：**experimental / opt-in / state-only**。当前代码与无 vendor 依赖测试已完成；本机缺少 `unitree_go` 和 `rmw_cyclonedds_cpp`，因此 **UNITREE ROS2 RUNTIME NOT VERIFIED ON JAZZY**。未发送控制消息，未做 Go2 真机验证。

## 1. Purpose

本实验不是为了增加第三个 Fleet robot，也不是 DR02 + Go2 concurrent fleet。它用同一个 `robot_02` slot 做 vendor substitution：

```text
DR02 Pro / drdds                Go2 / unitree_go
         ↓                              ↓
DeepRoboticsStateAdapter       UnitreeStateAdapter
         └──────────────┬───────────────┘
                        ↓
 RobotRegistry.record_heartbeat(recover_offline=False)
                        ↓
          stable internal Fleet model
```

验收重点是加入 Unitree 后不修改 Dispatcher、HaulTaskController、RobotExecutionContext、robot/task state machine 或数据库 schema。

## 2. Official SDK audit

事实源为 Unitree 官方仓库当前默认分支，审计日期 `2026-08-23`：

- [`unitree_sdk2`](https://github.com/unitreerobotics/unitree_sdk2/tree/9754cd153af3da471b0fe5f3aa535e426fb11db3)，commit `9754cd153af3da471b0fe5f3aa535e426fb11db3`
- [`unitree_ros2`](https://github.com/unitreerobotics/unitree_ros2/tree/668d1ec5a05d1c38d3306bdca7d59f2ba3581a88)，commit `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88`
- [`unitree_mujoco`](https://github.com/unitreerobotics/unitree_mujoco/tree/ae6a8403e272733e9996ef59990880330496177f)，commit `ae6a8403e272733e9996ef59990880330496177f`

| Audit item | Current finding |
| --- | --- |
| SDK2 DDS implementation | Unitree SDK2 bundles CycloneDDS `0.10.2` headers/libraries and exposes `ChannelFactory` / `ChannelPublisher` / `ChannelSubscriber`. |
| `unitree_ros2` bridge model | It supplies ROS 2 interface packages; compatible DDS wire types let ROS 2 processes communicate with Unitree DDS without a repository-local topic bridge node. |
| Official tested ROS 2 | Ubuntu 20.04/Foxy and Ubuntu 22.04/Humble; Humble is recommended. Jazzy is not listed. |
| Required RMW | Official setup selects `rmw_cyclonedds_cpp`; this is required for the documented direct Unitree DDS path. |
| Go2 message package | `unitree_go` |
| LowState ROS type | `unitree_go/msg/LowState` (`unitree_go.msg.LowState` in Python) |
| Simulator messages | `LowCmd`, `LowState`, `SportModeState`; `IMUState` on `rt/secondary_imu` is G1-only. Current simulator scope is described as low-level development. |

### Environment compatibility result

| Item | Result |
| --- | --- |
| OFFICIAL ENVIRONMENT | Foxy on Ubuntu 20.04; Humble on Ubuntu 22.04 (recommended) |
| CURRENT ENVIRONMENT | ROS 2 Jazzy |
| Local `unitree_go` | not installed / not sourced |
| Local `rmw_cyclonedds_cpp` | not installed |
| COMPATIBILITY RESULT | code/unit tests only; Jazzy build and runtime not verified |

没有修改 vendor repository，也没有把 Unitree 加入本包的默认依赖。

## 3. Go2 / MuJoCo architecture

官方当前 C++ simulator 启动方式是：

```bash
cd unitree_mujoco/simulate/build
./unitree_mujoco -r go2 -s scene_terrain.xml
```

默认配置语义：

```yaml
robot: go2
domain_id: 1
interface: lo
```

Go2 simulator 内部 publisher 使用 native SDK2 DDS channels：

```text
MuJoCo Go2
  ├─ rt/lowstate       : unitree_go LowState
  └─ rt/sportmodestate : unitree_go SportModeState
```

本实验选择 `LowState`，因为它是 simulator 明确生成的基础电机/IMU/电源状态流，也不会诱导 adapter 把 `SportModeState.position/velocity` 误当成 Fleet pose。adapter 不读取 LowState 中的 battery 字段；第一版只把合法 message delivery 映射为 transport liveness。

## 4. Unitree DDS / CycloneDDS architecture

Unitree 的 native SDK2 channel 名是 `rt/lowstate`。ROS 2 默认 DDS topic mapping 会为普通 ROS topic 加 `rt/` 前缀，所以 ROS graph / rclpy 一侧订阅：

```text
ROS topic:       /lowstate
DDS topic:       rt/lowstate
ROS message:     unitree_go/msg/LowState
SDK2 DDS type:   unitree_go::msg::dds_::LowState_
```

因此本仓常量是 `/lowstate`，不是把 `rt/lowstate` 直接交给 rclpy。

官方 `unitree_ros2` 环境设置包括：

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces>
  <NetworkInterface name="lo" priority="default" multicast="default" />
</Interfaces></General></Domain></CycloneDDS>'
```

- `RMW_IMPLEMENTATION` 让 ROS 2 使用 CycloneDDS RMW，以匹配 Unitree SDK2 的 DDS implementation 与 wire contract。
- `CYCLONEDDS_URI` 配置 CycloneDDS participant 的 network interface；它不替代 message type、topic、QoS 或 domain compatibility。
- simulation 使用 domain `1` + loopback `lo`，避免与默认真机 domain 混淆并把 discovery/data traffic 限定在本机。
- real robot 使用 domain `0` + 连接机器人的物理 NIC；官方示例主机地址为 `192.168.123.99/24`。
- `ROS_DOMAIN_ID` 必须与 simulator/robot 的 DDS domain 一致：simulation `1`，real robot `0`。

Unitree 比 DR02 文档更显式暴露 interface，是因为 SDK2 API 本身用 `ChannelFactory::Init(domain_id, interface)` 建立 DDS participant，官方 sim-to-real 示例也用 `domain/interface` 二元组切换本机 loopback 与物理网卡。这不表示两家的 pub/sub 原理完全不同；差异在 middleware packaging、network binding 和 vendor contracts。

## 5. Actual telemetry topic / type / QoS

| Layer | LowState | SportModeState |
| --- | --- | --- |
| Native SDK2 / MuJoCo DDS channel | `rt/lowstate` | `rt/sportmodestate` |
| ROS 2 topic | `/lowstate` | `/sportmodestate` |
| ROS 2 type | `unitree_go/msg/LowState` | `unitree_go/msg/SportModeState` |
| Current simulator support | yes | yes |
| Selected by this adapter | **yes** | no |

官方 `unitree_ros2` Go2 `read_low_state.cpp` 对 `unitree_go::msg::LowState` 使用 topic `lowstate` 与 depth `10`。本仓按同一 ROS-side contract 使用 `/lowstate`、depth `10`。在当前 Jazzy 的 `rclpy` 中，整数 depth `10` 解析为 `KEEP_LAST / RELIABLE / VOLATILE / depth 10` subscriber profile。

**Runtime boundary：** 由于本机没有 Unitree ROS 2 packages 和 CycloneDDS RMW，本轮无法执行 `ros2 topic info --verbose /lowstate`，所以 simulator publisher 的实际 endpoint QoS、delivery rate、publisher/subscriber count 均为 **NOT VERIFIED**。不得把 source-level subscriber configuration 写成 runtime parity PASS。首次 vendor runtime 时必须以 endpoint 输出为准，必要时再调整 subscriber QoS。

## 6. Adapter data flow

```text
Go2 MuJoCo publishes LowState
→ CycloneDDS discovery / serialization / transport
→ rclpy delivers unitree_go.msg.LowState on /lowstate
→ UnitreeStateAdapterNode callback
→ receive_count += 1
→ RobotRegistry.record_heartbeat(robot_02, recover_offline=False)
→ SQLite robot_02 last_heartbeat + updated_at
```

禁止从这一帧推断或修改：

- `RobotState`（尤其 OFFLINE 不自动恢复成 IDLE）
- `current_task_id`
- `current_station`
- Fleet `battery`
- pose、navigation state、task status 或 execution capability

## 7. Optional dependency boundary

`unitree_go` 与 `rclpy` 都在 standalone node 启动时 lazy import。普通 `import amr_warehouse_sim`、Fleet tests、AMR/Nav2/Mock WMS 不依赖 Unitree。

缺少 Unitree message package 时 fail-fast：

```text
Unitree integration requires the Unitree ROS 2 message packages.
Source the unitree_ros2 workspace before running this optional integration.
```

CLI 使用同一个 replacement slot：

```bash
ros2 run amr_warehouse_sim unitree_state_adapter \
  --robot-id robot_02 \
  --fleet-db /path/to/unitree_experiment.db
```

若要保存 DR02 与 Go2 两次实验，使用不同 SQLite 文件；不要新增 `robot_03`，也不要把两次实验描述为 concurrent heterogeneous fleet。

## 8. Runtime evidence

### Code / unit evidence

- import 不要求 Unitree runtime dependency；
- telemetry 只更新 heartbeat / updated_at；
- OFFLINE、active task、station、battery 保持；
- SQLite persistence 已覆盖；
- missing `unitree_go` error 已覆盖；
- DR02 与 Unitree adapter parity 已覆盖；
- Fleet core 未修改。

### ROS / simulator evidence

| Check | Result |
| --- | --- |
| `ros2 pkg prefix unitree_go` | FAIL: package not found |
| `ros2 pkg prefix rmw_cyclonedds_cpp` | FAIL: package not found |
| Go2 MuJoCo process | NOT RUN |
| `/lowstate` publisher/type/QoS/hz/echo | NOT RUN |
| adapter receive count | NOT RUN |
| SQLite before/after runtime heartbeat | NOT RUN |
| Jazzy compatibility | **NOT VERIFIED** |
| Real Go2 | NOT TESTED |

### First runtime acceptance sequence

在官方支持的 isolated environment（优先 Humble）或经单独 Jazzy build 验证后：

```bash
# Simulator terminal: current official command/config
./unitree_mujoco -r go2 -s scene_terrain.xml

# ROS 2 diagnostic terminal
source /path/to/unitree_ros2/setup_local.sh
export ROS_DOMAIN_ID=1
ros2 node list
ros2 topic list
ros2 topic info --verbose /lowstate
ros2 topic hz /lowstate
ros2 topic echo /lowstate --once
ros2 interface show unitree_go/msg/LowState

# Adapter terminal, same RMW/domain/interface
ros2 run amr_warehouse_sim unitree_state_adapter \
  --robot-id robot_02 \
  --fleet-db /path/to/unitree_experiment.db
```

启动 adapter 后再次检查 `/lowstate` 的 subscriber count，并保存 SQLite before/after。若 graph 显示的实际 topic 不同，先核对 ROS namespace mapping、domain 与官方 checkout，不通过猜测修改常量。

## 9. Deep Robotics vs Unitree

| Layer | DEEPRobotics | Unitree |
| --- | --- | --- |
| Robot experiment | DR02 Pro | Go2 |
| ROS client / SDK | vendor SDK uses C++ `rclcpp`; adapter uses `rclpy` | SDK2 native Channel API + `unitree_ros2`; adapter uses `rclpy` |
| Message package | `drdds` | `unitree_go` |
| State topic | `/JOINTS_DATA` | ROS `/lowstate`; native DDS `rt/lowstate` |
| State type | `drdds/msg/Joints` | `unitree_go/msg/LowState` |
| DDS | ROS 2 DDS path in verified DR02 stack | bundled CycloneDDS 0.10.2 / SDK2 channel |
| RMW | runtime used the local ROS 2 stack; vendor docs do not expose an equivalent hard requirement in this experiment | official path explicitly selects `rmw_cyclonedds_cpp` |
| Network interface config | domain consistency documented; no vendor-specific adapter interface parameter | explicit `CYCLONEDDS_URI` interface binding; `lo` for sim, physical NIC for robot |
| Simulation domain | verified DR02 run used experiment domain `42` | official Unitree sim default `1` |
| Real robot domain | not established in this repo | official default `0` |
| Simulator | official MuJoCo | official MuJoCo |
| Simulator telemetry | `/JOINTS_DATA` | LowState + SportModeState (Go2) |
| Internal mapping | heartbeat only | heartbeat only |
| Fleet robot slot | `robot_02` | replacement `robot_02` |
| Fleet core changes | none | none |
| Runtime status here | MuJoCo ROS runtime verified | Jazzy runtime not verified |

共同点是 typed pub/sub、DDS discovery/serialization/transport、topic/type/QoS/domain compatibility，以及最后收敛到稳定 internal liveness semantic。不同点是 vendor message schema、topic mapping、middleware distribution、RMW/network setup、simulator messages 和控制 API；这些都应停留在 vendor boundary。

## 10. Limitations

- `UnitreeStateAdapter` 不是 `RobotExecutionContext`，没有 ready gate 或 navigation implementation。
- 未实现 LowCmd、Sport API、stand/walk、motor torque、`cmd_vel` bridge 或 Nav2 integration。
- 未把 SportModeState pose 映射到 Fleet pose。
- 未证明 Jazzy compatibility、publisher QoS compatibility、message rate 或 real-robot connectivity。
- standalone adapter 只持久化 SQLite；其他已运行 Fleet process 不会自动刷新其 in-memory registry。
- 当前实验不证明 concurrent heterogeneous task execution，也不证明 Go2 warehouse task success。

## 11. Simulation vs real robot

| Concern | Simulation | Real Go2 |
| --- | --- | --- |
| DDS domain | `1` | `0` default |
| Interface | `lo` | robot-connected physical NIC |
| Host addressing | loopback | official example `192.168.123.99/24` |
| Telemetry source | MuJoCo bridge | robot service / DDS publisher |
| SportModeState | simulator keeps publishing it | availability depends on built-in motion service state |
| Safety | read-only process boundary | requires hardware/network/developer-mode preflight even for diagnostics |
| Evidence in this repo | code/unit only | none |

## 12. Portability conclusion

第二家 vendor 接入只新增 sibling adapter、optional ROS wrapper、tests、CLI 和 documentation。`fleet/dispatcher.py`、`fleet/haul_executor.py`、`fleet/execution_context.py`、`fleet/task_lifecycle.py`、robot state machine 与 schema 均不需要变化。

因此现有 Fleet internal model 对本轮“vendor telemetry → transport liveness”用途是 vendor-neutral。这个结论不外推到 navigation/control：未来第三家只读 telemetry 接入应修改其 vendor integration package、message import、topic/QoS/config 与文档；只有真实 task execution 需求出现时，才另行提供符合现有 `RobotExecutionContext` 的 execution implementation。
