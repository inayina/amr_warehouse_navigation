# 工业巡检系统设计面试指南

日期：`2026-08-24`

状态：基于当前仓库事实的 Reference Architecture 讲解；P0-3 Nav2/Mock 单点闭环已实现，不是完整巡检系统说明

## 1. 使用方式

这不是背答案合集。面试时先说明当前项目事实，再说明 extension design：

```text
CURRENT
  单 Gazebo AMR / Nav2
  fixed task points
  Mock WMS create/query/writeback
  ready gate
  demo Robot Registry / Dispatcher / heartbeat / resource lock
  three vendor state/liveness experiments

PROPOSED
  Inspection Plan / Task / Route / Run
  arrival verification
  inspection action / sensor acquisition
  data quality / evaluation
  evidence / finding / alarm / report
  capability-aware dispatch
  future Management Plane integration
```

先给 boundary，能避免把系统设计题回答成“我已经做过三家机器人巡检”。

## 2. 面试事实卡

| Question | 当前项目可证明的事实 | 不能声称 |
| --- | --- | --- |
| Nav2 | 四个 fixed points 有 historical fresh-session `SUCCEEDED`；当前 baseline 文件从该报告提交到 HEAD 未变化 | real robot、现场巡检、每点长期稳定 |
| Ready gate | 检查 5 个 lifecycle node、`map -> odom`、`/navigate_to_pose` server；not-ready 时 task 保持 pending | action visible 就等于 ready；ready 就等于 safe/inspection ready |
| Mock WMS | SQLite/CLI/HTTP/executor 状态闭环 | 完整 WMS、生产 backend、多车 scheduler |
| Fleet | Registry、static-cost Dispatcher、haul FSM、heartbeat/offline、pickup 前 reassign、resource lock 有 pytest evidence | Gazebo/Nav2 双车、生产恢复、完整 traffic management |
| Execution seam | `RobotExecutionContext` 有 ready + navigate，Fleet 可注入 fake/simulated context | 三家 vendor execution context 已实现 |
| Vendor | DR02/Unitree/Agibot adapters 只映射 liveness；逐家证据成熟度不同 | command、capability、inspection、real robot task success |
| Platform | 只读参考对象模型；AMR 当前未集成 | Platform 已调度 AMR 或参与 safety loop |
| Inspection P0-3 | opt-in executor 复用现有 `RosNav2Runtime`；fresh headless `candidate_dock_a` + Mock inspection report 有 live simulation 证据 | 真实 arrival verifier、真实 sensor、生产 artifact store、现场巡检 |
| 当前测试 | `2026-08-24` 本地 `162 passed, 7 skipped` | 未重跑 vendor runtime 或真机 |

事实入口：

- [Current Capability Audit](./INSPECTION_SYSTEM_REQUIREMENTS.md#2-current-capability-audit)
- [固定点位 fresh-session 报告](../wms/reports/fixed_task_points_success_matrix_regression_2026_05_15.md)
- [Mock WMS HTTP executor E2E 报告](../wms/reports/mock_wms_http_executor_end_to_end_validation_2026_05_14.md)
- [Fleet / EMS Design](../fleet/EMS_FLEET_DESIGN.md)
- [Vendor Validation Report](../fleet/VENDOR_VALIDATION_REPORT.md)

## 3. 90 秒系统设计回答

> 我会把这个问题定义成 brownfield 多品牌机器人巡检，而不是采购选型：现场已经有不同机器人，目标是统一任务和证据，同时保留各 vendor 的真实 SDK、控制和安全边界。
>
> 我当前项目已经有一条可复用链路：Mock WMS 创建固定点任务，executor 先检查 Nav2 lifecycle、TF 和 action server，再发 `NavigateToPose`，最后把结果写回 SQLite/HTTP；旁边还有 demo 级 Robot Registry、Dispatcher、heartbeat/offline、取货前重分配和 resource lock。三家 vendor 目前只做到 state/liveness adapter，command 和巡检能力没有实现。
>
> 巡检扩展不会推翻这条链，而是在 navigation 后增加 Arrival Verification、Stabilization、Inspection Action、Sensor Acquisition、Data Quality、Evaluation、Evidence 和 Finding/Report。核心 invariant 是 `NavigateToPose SUCCEEDED` 不等于 inspection point success。
>
> Dispatcher 先按 local liveness、business state、required capability、capability evidence 和 resource 形成 eligible set，再在 eligible set 内算 distance/cost，绝不按 vendor name 分支。Vendor 决定怎么接入，capability 决定能不能接任务。
>
> 系统拆成 control、state、inspection data 和 management 四个 plane。Nav2、watchdog、E-stop、关键阈值留在 edge；Go Platform 未来只做 Robot/Device/Runtime/Run identity、历史和 artifact reference。Platform 掉线不能破坏本地 safety。MVP 会先用一个 AMR、一个点、mock sample 和 deterministic rule，验证 navigation success 与 inspection success 的状态边界，再扩多点、capability Fleet 和真实 vendor/sensor。

## 4. 5 分钟展开回答

### 0:00–0:40 场景与边界

- 场景是工业园区已有多来源移动机器人，需要周期巡检和异常复核；
- 不把 DR02/Go2/D1 MaxPro 说成采购组合或已完成巡检；
- 当前项目是 AMR Warehouse Navigation，巡检是 extension design。

### 0:40–1:25 当前可复用能力

画出：

```text
Mock WMS Task
-> Ready Gate
-> NavigateToPose
-> Result Writeback

Robot Registry
-> Dispatcher
-> Assignment / Haul FSM
-> Heartbeat / Resource
```

说明：

- current Nav2 是单 Gazebo AMR；
- Fleet 是 pure Python/simulated-context demo；
- vendor adapters 只写 heartbeat，且 `recover_offline=False`；
- state plane 与 command plane 当前断开。

### 1:25–2:20 巡检业务闭环

画出：

```text
Plan -> Task -> Route -> Eligibility -> Assignment
-> Navigate -> Arrival -> Stabilize -> Inspect
-> Acquire -> Quality -> Evaluate -> Evidence
-> Finding/Alarm -> Next Point -> Run Report
```

重点讲 point success predicate：navigation、arrival、action、quality、evaluation、evidence、acceptance 全部通过。

### 2:20–3:10 状态与故障

分三套状态：

- Business：`PENDING -> ASSIGNED -> IN_PROGRESS -> terminal`；
- Assignment：`ASSIGNED -> EXECUTING -> COMPLETED/FAILED/RELEASED`；
- Execution：`NAVIGATING -> ARRIVED -> STABILIZING -> ACQUIRING -> VALIDATING -> EVALUATING -> POINT_SUCCEEDED`。

用两个例子证明分离：

1. sensor unavailable：execution fault，不能叫 transformer anomaly；
2. anomaly detected：point 可成功完成，但产生 business finding/alarm，不是 robot failure。

### 3:10–4:00 Capability 和 vendor

```text
eligible = online/fresh
        AND business state allowed
        AND capability match
        AND evidence threshold met
        AND resource available
```

- Integration evidence 与 capability maturity 两轴分开；
- `VERIFIED telemetry` 不能升级成 `HW_VERIFIED visual_inspection`；
- Dispatcher 不知道 ROS topic、DDS domain、TCP 或 vendor class。

### 4:00–4:35 Edge / Platform / Evidence

- Edge：navigation、local safety、watchdog、acquisition、basic quality、critical threshold、buffer；
- Platform：identity、RuntimeSession、management liveness、Run history、artifact reference、report/dashboard；
- metadata 与 large artifacts 分开，图片不塞当前 SQLite；
- Platform offline 只产生 management gap，不改变 local safety。

### 4:35–5:00 MVP 与风险

- Phase 1：一个 AMR、一个 point、mock sample、rule、report；
- Phase 2：multi-point run；
- Phase 3：fixed profile 的 capability-aware dispatch；
- Phase 4：一次一个 vendor execution/sensor，再做 Platform/UI。

最大风险不是“模型精度”一个点，而是 authority 和 evidence 被混用：liveness 当 readiness、navigation 当 inspection、vendor source audit 当 hardware capability、Platform projection 当 local truth。设计用分 plane、分状态、分 evidence 和 fail-closed eligibility 控制这个风险。

## 5. 架构图怎么画

### 5.1 第一张：业务和组件主链

从左到右先画 control：

```text
Operator/Plan
-> Task Service
-> Fleet Dispatcher
<-> Registry/Capability
-> Run Orchestrator
-> RobotExecutionContext
-> Nav2 / future vendor execution
-> Robot
```

再从 Robot 往回画 inspection data：

```text
Robot Sensors
-> Inspection Action
-> Observation
-> Quality
-> Evaluation
-> Finding/Result
-> Evidence/Report
```

最后把 Management Plane 画在旁边，用虚线连接 Robot/Runtime/Run/evidence reference，并在虚线上写：

```text
asynchronous projection
NOT IN CONTROL LOOP
```

在 `Nav2 -> Robot` 上标 `CURRENT single AMR`；在 vendor command、sensor、evaluation、Platform sync 上标 `NOT IMPLEMENTED / PROPOSED`。

### 5.2 第二张：四个 plane

画四个框：

1. Control：Task -> Dispatcher -> Execution -> command；
2. State：Telemetry -> Adapter -> Registry；
3. Inspection Data：Sensor -> Observation -> Analysis -> Evidence；
4. Management：Robot/Runtime/Run -> Platform -> Dashboard。

面试官追问为什么拆时，回答 latency、authority、data volume 和 failure consequence 都不同。

## 6. 二十个高频追问

### Q1. 你当前到底做到了什么，哪些只是设计？

当前做到了单 AMR Gazebo/Nav2 fixed-point execution、Mock WMS create/query/writeback、Nav2 ready gate，以及 pytest 验证的 demo Fleet Registry/Dispatcher/haul/heartbeat/resource。Inspection P0-3 已通过 opt-in executor 把现有 `RosNav2Runtime` 接到单点 Mock acquisition、quality、versioned rule、local JSON evidence 与 report。三家 vendor 仍只是 opt-in state/liveness integration experiment。

完整 Inspection Plan、多点 Run、ROS/Nav2 arrival verifier 接线、inspection action、真实 sensor acquisition、artifact store、alarm/report、capability dispatcher 和 Platform sync 都是 proposed/not implemented。这个回答必须先于任何巡检架构展开。

### Q2. 为什么不新做一套巡检任务系统？

当前已有稳定的 task intake、ready gate、NavigateToPose 和 writeback。巡检与仓储任务共享“高层意图 -> 选择执行者 -> 到点 -> 结果回写”的骨架。应扩展 task contract 和到点后的 domain action，不应复制 Nav2 或另起一个绕过 ready gate 的 executor。

这样还保留现有单车 baseline 的回归入口，符合项目中 task layer 不反向修改 Nav2 的约束。

### Q3. 巡检 Task、Run、Point 为什么分开？

- Task 表达业务意图和 acceptance policy；
- Run 表达 task 的一次执行尝试、robot/profile/runtime correlation；
- Point 是 route 中一个可独立 retry 和取证的步骤；
- PointAttempt 保留每次采集和失败 evidence。

如果 A/B/C 三点拆成三个无关联 haul task，就无法得到一致的 route order、policy snapshot、partial result 和一份 run report。

### Q4. 为什么 Navigation success != Inspection success？

当前 `mock_wms_executor` 在 Nav2 `STATUS_SUCCEEDED` 后直接把单点 task 写成 `succeeded`，这对最小仓储导航任务成立。但巡检还需要：

```text
arrival tolerance
-> stabilization
-> action
-> acquisition
-> data quality
-> evaluation
-> evidence persistence
```

Nav2 只证明到达其 goal tolerance，不能证明 camera 稳定、设备在视野、sample 新鲜或 report 可追溯。因此架构新增 `ARRIVED` candidate 和 point acceptance gate。

### Q5. 为什么 state / control / data / management plane 分离？

- State plane 接受 observation，但不直接发 command；
- Control plane 改变机器人/任务状态，需要明确 owner、timeout、cancel；
- Inspection data plane 保存大体积、可重放、有 provenance 的数据；
- Management plane 做低频全局历史和投影。

当前 vendor adapter 的设计已经证明一个好边界：telemetry 只调用 `record_heartbeat(recover_offline=False)`，不改 task、station、battery 或 capability。四 plane 是把这个窄边界推广到完整巡检系统。

### Q6. 为什么 vendor SDK 要用 adapter？

三家真实 interface 不一样：DR02 是 ROS 2/DDS typed topic，Unitree 有 CycloneDDS/ROS 2 setup，Agibot 是 C++ SDK/TCP 加 process JSONL。若上层直接依赖这些 transport，Dispatcher 会承担 topic/QoS/domain/ABI/process lifecycle。

Adapter 的职责是验证并归一化 state；未来 execution implementation 独立封装 command/result/cancel。Vendor schema 停在 integration boundary，上层只看内部 contract。

### Q7. 为什么 Dispatcher 不应该知道 vendor？

品牌是“如何接入”的 inventory metadata，不是“能否完成任务”的业务条件。业务资格来自 capability、evidence、state 和 resource。

按 vendor 分支会产生三个问题：

1. 把采购历史固化到业务规则；
2. 同能力 robot 不能替换；
3. adapter/source audit 容易被误当成 task capability。

所以先形成 eligible set，再算 cost；vendor 只用于 adapter selection 和 diagnostics。

### Q8. 为什么需要 heartbeat？

Registry 里的 `IDLE` 可能是陈旧业务状态。当前 Dispatcher 已要求 heartbeat fresh，HeartbeatMonitor 能把 stale robot 标为 `OFFLINE`，并在 pickup 前 demo requeue。

巡检里仍需要 heartbeat，但要说明 source：vendor telemetry liveness、local execution runtime heartbeat、Platform RuntimeHeartbeat 是不同事实。Heartbeat 只回答 freshness，不回答 ready/safe/capable。

### Q9. 机器人掉线怎么处理？

先按阶段判断可逆性：

- dispatch 前：reject candidate，选别的 eligible robot；
- navigation 中：先确认旧 command/goal owner 已安全结束，再决定 release/reassign；
- acquisition 中：当前 PointAttempt 失败，保留 partial evidence；只有 item 幂等且另一 robot capability 合格才从新 attempt 重做；
- 已完成不可逆 action：不自动重分配，转人工/恢复 policy。

这继承了当前 haul 的“pickup 前可 requeue、pickup 后阻止重分配”原则，但巡检的 irreversible boundary 要按 point/action 重新定义。

### Q10. Platform 掉线怎么办？

Platform 不在同步 execution path。已接受任务由 local policy 决定继续或安全停止；E-stop、watchdog、Nav2、local threshold 和 safe stop 不依赖 Platform。Run/evidence projection 在本地 bounded buffer，Platform 恢复后按 idempotency contract 同步，并明确 gap/stale。

当前 Go Platform README 也把它定位为 management plane，AMR 当前未集成。因此这是 future boundary，不是已验证链路。

### Q11. Sensor 数据如何校验？

先做 Data Quality Gate，再做 anomaly evaluation。至少检查：

- capture/receive time 与 freshness；
- schema/type/range；
- completeness 和 sequence；
- robot/point/pose association；
- frame/calibration/version；
- item-specific quality，例如清晰度、信噪比或覆盖范围。

stale 或 invalid sample 产生 `DATA_INVALID`/system fault，不得直接进入“设备正常”或“设备异常”。

### Q12. Anomaly detection 怎么设计？

分三类：

1. deterministic rule，例如 temperature threshold；
2. classical signal/CV，例如 gauge reading、spectrum、ROI；
3. ML/AI，例如 visual anomaly model。

统一 evaluator result contract，但保留 evaluator type/version/input provenance。安全关键阈值在 edge 可独立执行；non-real-time AI 可在 Platform。confidence 不能替代 quality gate 和 severity policy。

### Q13. Inspection evidence 怎么保存？

结构化 metadata 与 artifact payload 分开：

- DB 保存 run/task/robot/point/attempt/time/pose、quality、evaluation、finding、URI/hash/version；
- artifact store 保存 image/audio/thermal/log；
- report 聚合引用，不复制或覆盖原始事实。

当前 SQLite 可借鉴 metadata persistence pattern，但不直接塞图片 blob。MVP 可先用本地 directory + hash/reference，明确不是 production object storage。

### Q14. 为什么不能全部上 AI？

因为问题类型、延迟和 failure consequence 不同：temperature/gas limit 是确定性安全阈值；gauge/audio 可能用 classical algorithm 更可解释；复杂视觉才需要 ML。全部上 cloud AI 会引入网络依赖、不可解释 failure、model drift 和无法保证 local safety 的问题。

AI 只能成为 evaluator 之一，不能替代 data quality、deterministic threshold、evidence provenance 或 human escalation。

### Q15. Capability-based dispatch 怎么做？

```text
registered
AND local liveness valid
AND business state allowed
AND no active task
AND required capability match
AND maturity >= deployment policy
AND resource available
THEN cost ranking
```

每个 rejection 返回 typed reason；每个 assignment 冻结 profile/policy/evidence snapshot。Capability 缺失或 evidence 不足 fail closed。当前 Dispatcher 只实现前三类 availability 与 static station cost，因此 capability 部分明确是 proposed。

### Q16. 如何从单机器人扩展到多机器人？

先不复制 Gazebo launch，而是分层推进：

1. 保持 single robot execution contract；
2. 用 fake contexts 验证多个 robot 的 identity、eligibility、assignment uniqueness；
3. 加 resource ownership 和 per-robot executor lifecycle；
4. 再做双 Nav2 namespace/TF/action isolation；
5. 最后做 traffic/conflict acceptance。

当前 Stage 6 正因为 namespace、TF、Gazebo entity、action/server 和 executor isolation 未冻结而 deferred。这是诚实的扩展路径。

### Q17. Real-time 和 non-real-time 怎么划分？

Local/latency-sensitive：controller、E-stop、watchdog、lost-command safe stop、sensor acquisition timing、critical threshold。

Non-real-time：plan management、historical report、cross-run analytics、artifact indexing、non-critical AI、Dashboard。

Fleet dispatch 是 site-local control coordination，但不进入 motor servo loop；Platform 是 management，不能发 joint command 或 `/cmd_vel`。

### Q18. ROS 2 / DDS 在哪里？

当前 AMR 内：ROS 2 launch、TF、lifecycle、`NavigateToPose` action、Nav2 nodes；Gazebo bridge 提供传感与 `/cmd_vel` 执行链。

Vendor boundary：DR02/Unitree state adapter 通过各自 ROS 2/DDS contract；Agibot 高层 SDK不是 ROS 2，而是 C++/TCP，再通过 JSONL process boundary 进入 Python adapter。

因此 ROS 2/DDS 是重要 transport，但不是强迫所有 vendor 使用的 universal business interface。

### Q19. Go Platform 在哪里？

它位于 Management Plane，未来负责：

- Robot/Device/Runtime identity；
- RuntimeSession/RuntimeHeartbeat history；
- Run correlation；
- artifact/report references；
- API/Dashboard aggregation。

`InspectionRun` 可以映射到 Platform `Run` envelope，但 point/evaluation/result truth 仍由 inspection domain 拥有。Platform 不替代 Nav2、不控制 `/cmd_vel`、不拥有 E-stop/watchdog，也不推断 task success。当前 AMR 与 Platform 未集成。

### Q20. 系统最大的工程风险是什么？

第一风险是**语义与 authority 被越级合并**：

- telemetry alive 被当作 ready；
- online 被当作 capability；
- Navigate success 被当作 Inspection success；
- source/mock evidence 被当作 hardware qualification；
- Platform stale projection 被当作 local truth；
- sensor fault 被当作 asset anomaly。

第二风险是真实 vendor command/safety contract 未被逐家验证。第三风险是 sensor data 与 pose/calibration/evaluator provenance 不完整，导致报告看似完整但不可复核。

架构对策是窄 contract、四 plane、三状态、两条 evidence 轴、fail-closed eligibility、point attempt 与 immutable evidence。

## 7. 常见反问与应答边界

### “三家机器人都能巡检吗？”

不能这样说。当前只有三家 state/liveness integration experiment；command/inspection paths 未实现，真机巡检均未验证。Reference Design 说明如何让未来合格能力进入同一个 Fleet，不是当前 capability claim。

### “为什么不直接给 Unitree/DR02 加 if 分支？”

因为 task 需要的是 capability，不是品牌。Vendor branch 应停在 integration/adapter factory 或 deployment config；Dispatcher 的 eligibility 只看 internal profile/evidence/resource/state。

### “你已经有 resource lock，是不是 traffic management 做完了？”

不是。当前只验证逻辑 ownership、FIFO、timeout、ordered acquire，且尚未接 haul execution。没有 multi-agent path planning、zone trigger、priority/preemption、deadlock recovery 或现场互锁。

### “135 tests 是否证明系统可上线？”

不证明。它说明当前 Python contract/regression baseline 通过；live Nav2 使用历史报告，vendor runtime/hardware 与 inspection runtime没有在本轮执行。上线还需要现场、硬件、安全、网络、性能和 evidence acceptance。

## 8. 白板结束语

可以用下面四句话收束：

1. 我复用当前 Task -> Ready -> Navigate -> Writeback，不重写 Nav2；
2. 我把 Arrival -> Inspect -> Quality -> Evidence 作为新的巡检 domain；
3. 我按 capability/evidence 调度，不按 vendor 调度；
4. 我让 Platform 管身份和历史，让 edge 管实时执行和安全。

## 9. Can this design be defended in an interview?

**YES，前提是严格按事实标签讲。**

可作为 current implementation 讲：

- 单 AMR Gazebo/Nav2 fixed-point baseline 和历史 live reports；
- Mock WMS SQLite/CLI/HTTP/executor/writeback；
- Nav2 ready gate；
- pytest 验证的 Fleet Stage 1–5 abstractions；
- 三家不同 transport 的 state/liveness integration experiments 及各自 evidence boundary。

只能作为 extension design 讲：

- Inspection Plan/Task/Route/Run；
- arrival/inspection/sensor/quality/evaluation/evidence/alarm/report；
- capability-aware Dispatcher；
- vendor command/inspection execution；
- Go Platform/Dashboard integration；
- real robot、真实 sensor 与现场 acceptance。

## 10. Related Documents

- [Inspection System Requirements](./INSPECTION_SYSTEM_REQUIREMENTS.md)
- [Inspection System Architecture](./INSPECTION_SYSTEM_ARCHITECTURE.md)
- [Fleet / EMS Design](../fleet/EMS_FLEET_DESIGN.md)
- [Task Lifecycle](../fleet/TASK_LIFECYCLE.md)
- [Multi-Vendor Architecture](../fleet/MULTI_VENDOR_ARCHITECTURE.md)
- [Vendor Validation Report](../fleet/VENDOR_VALIDATION_REPORT.md)
