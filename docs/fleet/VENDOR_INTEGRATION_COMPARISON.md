# Vendor Integration Architecture Comparison

日期：`2026-08-23`

口径：三种都是 opt-in、state-only architecture experiments；不是 concurrent heterogeneous fleet、task execution 或 production support。

| Layer | DEEPRobotics | Unitree | Agibot |
| --- | --- | --- | --- |
| Robot | DR02 Pro | Go2 | D1 MaxPro |
| Primary API | ROS 2 topic | ROS 2 messages over CycloneDDS-compatible wire | C++ abstract `Robot` API + prebuilt `.so` |
| Language boundary | vendor `rclcpp` publisher → our `rclpy` subscriber | SDK2 DDS publisher → our `rclpy` subscriber | vendor C++ process → stdout JSONL → Python |
| Transport exposed | ROS 2 / DDS | CycloneDDS, domain + interface binding | vendor TCP/socket hidden by SDK |
| Vendor contract | `drdds/msg/Joints` | `unitree_go/msg/LowState` | `high_level_base.h` structs/vtable + `.so` ABI |
| Vendor endpoint | `/JOINTS_DATA` | ROS `/lowstate`, DDS `rt/lowstate` | `createQuadruped/init/GetRobotStatus` |
| Adapter input | ROS callback | ROS callback | validated process IPC event |
| Optional dependency | `rclpy` + `drdds` overlay | `rclpy` + `unitree_go` + CycloneDDS RMW | external probe executable + official SDK at probe build/runtime only |
| Internal mapping | heartbeat only | heartbeat only | heartbeat only |
| Default Fleet slot | `robot_02` | replacement `robot_02` | replacement `robot_02` |
| Fleet core changes | none | none | none |
| Control tested | no | no | no |
| Simulator runtime | MuJoCo telemetry verified | not verified on Jazzy | no official simulator in audited repo |
| Real robot | not tested | not tested | not tested |

## What survived all three vendors

真正稳定的共同 contract 不是 ROS topic、DDS、C++ class 或 IPC technology，而是：

```text
validated vendor telemetry arrival
→ transport liveness event
→ RobotRegistry.record_heartbeat(recover_offline=False)
```

这条 contract 只允许改变 `last_heartbeat/updated_at`。Fleet business state、task、station、battery、pose 和 execution capability 必须由各自有明确 provenance 的 contract 更新。

## What remains vendor-specific

- dependency loading、message/ABI schema；
- topic/type/QoS/domain 或 IP/socket/firmware configuration；
- SDK lifecycle、thread/callback ownership、shutdown；
- telemetry validation 与 freshness；
- control/navigation/safety semantics；
- vendor-specific diagnostics。

## Refactor recommendation

当前值得共享的是 parameterized parity/contract test 与 documentation evidence template。三个 runtime adapter 的业务方法虽然都调用 `record_heartbeat(recover_offline=False)`，但 ROS node lifecycle 与 child-process lifecycle 完全不同；现在抽 `BaseVendorAdapter`、factory 或 generic transport 会把不稳定差异藏进条件分支，默认不实施。
