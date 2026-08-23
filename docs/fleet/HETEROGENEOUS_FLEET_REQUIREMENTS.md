# Heterogeneous Fleet Requirements

日期：`2026-08-23`
状态：**Requirements Design Only**
适用场景：reference industrial site 的 brownfield heterogeneous robot integration

## 1. Background

参考工业现场往往不是一次性采购同一品牌机器人，而是在不同项目周期陆续引入室内物流 AMR、人形机器人、四足机器人和边缘 Runtime。它们的 SDK、通信协议、生命周期、状态、诊断、控制语义和安全约束不同。

现场问题因此不是“选择哪一个品牌”，而是“已有多品牌设备如何进入同一运营体系，同时保留各自真实的控制和安全边界”。

当前项目已经证明的最窄公共链路是：

```text
vendor-specific telemetry
-> vendor-specific adapter
-> normalized liveness
-> RobotRegistry
```

当前 evidence 以 [MULTI_VENDOR_ARCHITECTURE.md](./MULTI_VENDOR_ARCHITECTURE.md) 和 [VENDOR_VALIDATION_REPORT.md](./VENDOR_VALIDATION_REPORT.md) 为准：DR02 telemetry runtime 为 `VERIFIED`；Unitree telemetry/command 为 `SOURCE-AUDITED`；Agibot compile/link 为 `VERIFIED`、mock IPC 为 `MOCK-VERIFIED`，三家真机均为 `NOT TESTED`。这些证据不证明 heterogeneous Fleet execution。

## 2. Problem Statement

### 2.1 现在出现的真实需求

1. **为什么需要 multi-vendor integration？** 同一现场已有不同 vendor interface；若没有统一内部边界，每次换机器人都会把 vendor transport、状态和故障语义扩散到任务系统。
2. **为什么不能继续维护彼此独立的 vendor application？** 独立应用会重复身份、存活、任务关联、告警和审计逻辑，操作员也无法获得一致的 fleet-wide view；更严重的是，各应用可能分别修改同一任务或机器人状态，形成多主写冲突。
3. **为什么 online/offline 不够？** online 只说明某条 transport/runtime 在时间窗口内有观测；它不说明机器人处于允许派发的业务状态、拥有任务所需能力、能力证据达到部署阈值、资源可用或本地 safety gate 已通过。
4. **为什么调度需要 capability？** 当前 `IDLE + fresh heartbeat + station cost` 只能在同质机器人假设下工作。异构机器人即使都 online/idle，也未必能满足相同任务要求。
5. **为什么 capability 不能只有 true/false？** 能力可能带适用环境、参数限制、软件/硬件版本和证据成熟度；`true` 无法区分 vendor 宣称、源码确认、模拟验证和真机验收，也无法表达未知、限制或证据失效。
6. **为什么 declared 与 verified 必须分开？** vendor 声明是候选能力来源，不是当前项目自动派发授权。只有经过项目定义的验证并达到 deployment policy 阈值，能力才可进入自动 eligibility。
7. **为什么 Management Plane 与 Execution Plane 分开？** Management Plane 负责身份、历史和低频运营投影；Execution Plane 必须在本地完成任务执行、watchdog 和 safety gate。两者的延迟、可用性和故障后果不同。
8. **为什么 Platform 故障不能影响本地安全？** Platform 网络或服务不可用是可预期的管理面故障，不得中断本地 watchdog、E-stop、控制器、Nav2 或安全停止路径。
9. **为什么 Dispatcher 不应按 vendor name 分配？** vendor 决定如何集成，不决定业务资格。按品牌分支会把采购历史固化到业务逻辑，并阻止等价能力的替换。
10. **为什么还不能声称 heterogeneous Fleet execution？** 目前只有 AMR/Nav2 有真实 execution；第三方 vendor 只形成不同成熟度的 state/liveness evidence，vendor-specific `RobotExecutionContext` 尚未实现，三家也没有共同任务或真机验收证据。

### 2.2 需求目标句

系统需要在不泄漏 vendor transport、不削弱本地安全、不扩大现有证据结论的前提下，依据**机器人当前可用性、所需能力、能力证据阈值和资源约束**确定任务 eligibility，并把运营信息投影到独立的 Management Plane。

## 3. Stakeholders

| Stakeholder | Need |
| --- | --- |
| Operations operator | 统一查看机器人身份、运行状态、当前任务、不可派发原因和诊断来源。 |
| Fleet administrator | 管理可进入某部署环境的机器人 profile、能力证据阈值和启停策略。 |
| Robot integration engineer | 将 vendor SDK/transport 归一化到内部 contract，并附带版本和验证证据。 |
| Maintenance engineer | 区分机器人、设备、Runtime、adapter 和网络故障，定位真实责任边界。 |
| Task/WMS system | 提交业务任务并获得稳定、vendor-neutral 的任务/结果状态。 |
| Robot runtime | 在本地执行任务、维护 operational state 和 safety gate，不依赖 Platform 实时响应。 |
| Vendor SDK | 提供 vendor-specific telemetry/control contract；不直接进入 Fleet business logic。 |

这里不假设真实客户组织结构或已经完成现场部署。

## 4. Existing System

### 4.1 AMR / Fleet 当前能力

- 单 AMR / Nav2 execution 与固定任务点；
- Mock WMS、pickup/dropoff haul lifecycle；
- Robot Registry、Fleet Dispatcher、heartbeat/offline、resource locking；
- vendor-neutral `RobotExecutionContext` seam；
- 三家 opt-in state/liveness integration experiment。

当前 Dispatcher 选择的是“available robot”：注册记录存在、heartbeat 未超时、业务状态允许、没有 active task，然后按静态 station cost 排序。它没有 capability profile、task requirement 或 evidence threshold。

### 4.2 robot-platform-service 当前能力（只读参考）

参考仓库当前 HEAD：`49509bd234d2076bf4595574f1b330518bbb58ad`。

其当前模型包含 `Robot`、`DeviceV2`、`Runtime`、`RuntimeSession`、`RuntimeHeartbeat` 和 `RunV2`，并明确：

- `Robot` 是跨 Runtime 重启保持稳定的资产身份；
- `Device` 是机器人上的计算、控制器、传感器等资产；
- `Runtime` 是可独立登记和观测的软件部署；
- `RuntimeSession` 是一次不可复用的进程生命周期；
- `RuntimeHeartbeat` 只形成 management-plane liveness；
- `Run` 是任务执行关联台账；
- Platform 不参与实时控制，且 AMR 当前尚未接入。

因此该概念集合适合作为未来 Management Plane envelope 的基础，但尚不足以表达 approved robot profile、capability snapshot、integration provenance 和 capability evidence reference。

## 5. Business Goals

| Goal | Required outcome |
| --- | --- |
| Vendor independence | 新增或替换 vendor 时，上层 task/Fleet logic 不直接依赖 vendor SDK。 |
| Unified observability | 统一查看 identity、runtime liveness、business state、current task 和 diagnostic provenance。 |
| Capability-aware eligibility | 调度从 available robot 升级为满足能力与资源约束的 eligible robot。 |
| Evidence-aware automation | vendor-declared 或 mock-only 能力不得自动升级成项目已验证能力。 |
| Failure isolation | Platform、网络或 adapter 故障不得破坏本地 safety/control loop。 |
| Replaceability | ROS 2、DDS、TCP、C++ SDK 和 IPC 保持在 integration boundary 内。 |
| Backward compatibility | 当前 pickup/dropoff haul 与单 AMR/Nav2 baseline 在空 capability requirement 下保持原行为。 |

业务目标不包含给三家 vendor 固定分配角色，也不包含采购决策。

## 6. User / Operator Needs

- 操作员需要看到“不可派发的具体原因”，而不是只有 online/offline。
- Fleet administrator 需要定义部署环境允许的最低 capability evidence，但不能修改 vendor runtime safety contract。
- Integration engineer 需要登记 capability claim 的来源、环境、版本和 evidence reference。
- Maintenance engineer 需要区分 `robot offline`、`adapter crashed`、`Platform unreachable`、`capability insufficient` 和 `evidence insufficient`。
- WMS 需要使用 vendor-neutral task requirement，不应提交 `assign_to: unitree` 一类品牌条件。
- 本地 Runtime 需要在 Platform 不可达时继续安全地执行或停止，并保留明确的同步缺口。

## 7. Functional Requirements

### P0 — first implementable slice

| ID | Requirement |
| --- | --- |
| `FR-P0-01` | 系统 SHALL 使用稳定的 robot identity；vendor/model 可作为 inventory/integration metadata，但不得替代内部 robot identity。 |
| `FR-P0-02` | Vendor adapter SHALL 把 vendor schema 归一化到明确的内部 state/liveness input；vendor message、DDS topic、TCP 或 C++ ABI 不得进入 Fleet core。 |
| `FR-P0-03` | 系统 SHALL 能表示 versioned Robot Profile 中的 capability identity、约束、claim source、maturity 和 evidence reference；不得只保存无来源 boolean。 |
| `FR-P0-04` | Task SHALL 可声明 `task_type`、`required_capabilities`、target/resource 和 execution requirements；这些字段对现有 haul task 必须可选并保持默认兼容。 |
| `FR-P0-05` | Dispatcher SHALL 先形成 eligible set，再计算 station/resource cost。eligible 至少要求：registered、local liveness usable、business state allowed、无冲突 active task、required capabilities 满足、evidence threshold 满足、resource constraints 满足。 |
| `FR-P0-06` | Dispatcher SHALL NOT 按 vendor name 分支；vendor 仅用于 adapter selection、inventory 和 diagnostics。 |
| `FR-P0-07` | 不满足 eligibility 的 robot SHALL 返回确定性的 reason code，至少区分 state、liveness、capability mismatch、evidence threshold 和 resource conflict。 |
| `FR-P0-08` | Capability profile 或 task requirement 缺失/不可解析时 SHALL fail closed；不得猜测 vendor 能力。 |
| `FR-P0-09` | Vendor telemetry arrival SHALL 只更新其有 authority 的观测；不得自动将 `OFFLINE` 恢复成 `IDLE`，不得推断 task success、pose、battery 或 capability。 |
| `FR-P0-10` | 现有 pickup/dropoff task 在 `required_capabilities` 为空时 SHALL 保持当前 lifecycle、requeue boundary、resource locking 和 cost selection 语义。 |

### P1 — management and evidence integration

| ID | Requirement |
| --- | --- |
| `FR-P1-01` | Fleet 与 Platform SHALL 通过显式 sync contract 交换 inventory、approved profile version、management heartbeat 和 run projection；第一阶段不得共享数据库。 |
| `FR-P1-02` | Platform SHALL 保存/聚合 Robot、Device、Runtime、RuntimeSession、RuntimeHeartbeat 和 Run envelope，并能引用 capability/evidence metadata；不保存 vendor control semantics。 |
| `FR-P1-03` | Capability evidence SHALL 包含 producer/issuer、robot/profile/version、environment、observed time、result、evidence reference 和 maturity；Platform 不得自行把 maturity 升级。 |
| `FR-P1-04` | System SHALL 提供 current operational state 与 management-plane projection 的 timestamp/source；UI 或 API 不得把陈旧投影显示为当前执行事实。 |
| `FR-P1-05` | Platform 不可达时，producer SHALL bounded-backoff；数据缺口必须可见，不得伪造补报时间或改变本地 execution state。 |
| `FR-P1-06` | Run history SHALL 引用 authoritative executor session 和 domain-owned result/evidence；Platform 只持有 correlation envelope。 |
| `FR-P1-07` | Profile/evidence 变更 SHALL 可审计，并且新的 eligibility 决策使用哪个 profile/policy version 必须可追溯。 |

### P2 — later proof and rollout

| ID | Requirement |
| --- | --- |
| `FR-P2-01` | 每个 vendor execution implementation SHALL 独立满足 `RobotExecutionContext` 的任务语义、timeout、cancel/result 和 safety contract，不能因 state adapter 存在而视为已实现。 |
| `FR-P2-02` | Simulator command proof SHALL 与 Fleet execution proof、real robot acceptance 分开记录。 |
| `FR-P2-03` | Real robot 自动 eligibility SHALL 要求 deployment policy 指定的 hardware evidence 和现场 safety acceptance。 |
| `FR-P2-04` | 多机器人 workflow、dashboard aggregation 和跨机器人任务 SHALL 在单机器人 capability-aware dispatch 稳定后单独定义需求。 |

## 8. Non-functional Requirements

| ID | Quality | Requirement |
| --- | --- | --- |
| `NFR-01` | Safety | Management Plane 和 capability metadata 不得位于 E-stop、watchdog、motor/joint control 或 local navigation safety 的闭环中。 |
| `NFR-02` | Isolation | 一个 vendor adapter 或 Platform 故障不得导致其他本地 Runtime 失去安全控制；故障影响范围必须可识别。 |
| `NFR-03` | Observability | 每个 eligibility/rejection、profile revision、evidence claim 和 state projection 必须带 timestamp、source 和 correlation identity。 |
| `NFR-04` | Replaceability | 增加等价 capability 的新 vendor adapter 不应修改 Dispatcher 的 vendor-specific branch。 |
| `NFR-05` | Backward compatibility | 当前 AMR/Nav2、Mock WMS、haul lifecycle、resource locking 和 tests 必须保持可运行。 |
| `NFR-06` | Failure containment | 外部 API、WMS 或 Platform timeout 不得阻塞 local safety loop；所有远端调用必须在控制闭环之外。 |
| `NFR-07` | Testability | Eligibility 输入必须可用固定 profile、固定 policy、固定 clock 和 fake execution context 做确定性测试。 |
| `NFR-08` | Auditability | 系统必须能解释“为什么该 robot 在该时刻被选中/拒绝”，并关联使用的证据版本。 |

当前实验规模不要求 HA cluster、Kubernetes、Kafka、service mesh 或 cloud-native deployment。

## 9. Robot Capability Requirements

### 9.1 推荐模型

Capability 不应是 vendor role，也不应是单个 boolean。需求层建议至少包含：

```text
capability identity
+ optional constraints/qualifiers
+ claim source
+ capability maturity
+ evidence reference
+ robot/profile/software/environment scope
+ validity or review state
```

`mobile`、`indoor_navigation`、`visual_inspection`、`payload_transport`、`manipulation`、`stairs` 可作为讨论用 seed vocabulary，但本轮不冻结完整 taxonomy，也不把它们绑定到任何 vendor。

### 9.2 两种 evidence model 应分开

当前 integration evidence：

```text
VERIFIED / SOURCE-AUDITED / MOCK-VERIFIED / NOT TESTED
```

它回答“某条 integration link 有什么证据”。Capability maturity 建议使用独立轴：

```text
DECLARED / SOURCE_AUDITED / SIM_VERIFIED / HW_VERIFIED
```

| Maturity | Requirement meaning |
| --- | --- |
| `DECLARED` | Vendor、datasheet 或 inventory claim 已登记；项目没有核对实现或运行行为。 |
| `SOURCE_AUDITED` | 当前 pin 的官方源码/SDK/document contract 已核对；没有证明目标能力在 simulator 或 hardware 中成功。 |
| `SIM_VERIFIED` | 在记录了 simulator、版本、配置、输入和判定标准的运行中通过；只适用于该仿真环境。 |
| `HW_VERIFIED` | 在指定真实机器人、固件、环境和安全验收条件下通过；不自动外推到其他部署环境。 |

它回答“某个 robot profile 在什么环境中证明了某项能力”。二者不应完全统一，原因是：

- `VERIFIED` 本身不说明 simulator 还是真机；
- `MOCK-VERIFIED` 可证明 parser/IPC，却不能证明机器人能力；
- 一条 telemetry link 被验证，不代表 navigation/manipulation capability 被验证；
- 同一 capability 可在不同软件版本、负载或环境下拥有不同 maturity。

两种模型应共享 evidence reference、source、time、environment 和 version provenance，但不得互相自动升级。

### 9.3 Capability eligibility

Capability presence 与自动 eligibility 分开。概念示例：

```yaml
task:
  required_capabilities:
    - identity: mobile
deployment_policy:
  minimum_capability_maturity: SIM_VERIFIED
```

只有 `mobile` claim 且 maturity 达到 policy threshold 的 robot 才可进入自动 eligible set。`DECLARED` 或 integration-only evidence 不满足该阈值。这里定义的是 requirement concept，不是 policy engine 设计。

## 10. Task Requirement Model

现有 haul task 的 `pickup_station` / `dropoff_station` 保持有效。未来 task envelope 需要可选扩展：

| Field concept | Requirement |
| --- | --- |
| `task_type` | 初始 reference taxonomy：`TRANSPORT / INSPECTION / RESPONSE`；不在本轮冻结完整枚举。 |
| `required_capabilities` | capability identity + optional constraints + minimum maturity override。 |
| `priority` | 用于 eligible tasks 之间的调度优先级，不绕过 safety/evidence gate。 |
| `target/resources` | 保留现有 station/resource 语义，并允许 domain-specific target reference。 |
| `execution_requirements` | 描述 timeout/cancel/result 等 contract 需求，不携带 vendor command。 |

第一阶段不需要 DAG、behavior tree、LLM task planning 或 multi-agent planning。

## 11. Management Plane Requirements

### 11.1 Concept fit

参考 Go Platform 的现有概念基本覆盖 identity/lifecycle envelope：

| Existing concept | Required role |
| --- | --- |
| Robot | physical/logical robot identity。 |
| Device | onboard/edge compute、controller、sensor 等 inventory。 |
| Runtime | Nav2、vendor adapter、edge runtime 或 service deployment identity。 |
| RuntimeSession | 一次 process lifecycle。 |
| RuntimeHeartbeat | management-plane liveness observation。 |
| Run | task/execution correlation and historical reference。 |

未来可能需要 `RobotProfile`、`CapabilitySnapshot`、`IntegrationSource`、`EvidenceReference`；它们是 requirement proposals，不是本轮 schema 变更。是否分别建实体、作为 versioned document 或 typed reference，留到 R1 domain design 决定。

| Proposed concept | Requirement purpose |
| --- | --- |
| RobotProfile | 一台 robot 在某 deployment policy 下获批的、版本化的能力与约束集合。 |
| CapabilitySnapshot | 一次 eligibility/run 使用的不可变 profile/policy 解析结果，供事后解释。 |
| IntegrationSource | 标识 adapter、vendor SDK/source commit、transport 和 producer Runtime。 |
| EvidenceReference | 指向 simulator/hardware report、log、artifact 或 acceptance record，不复制域内产物。 |

### 11.2 Management authority

- Platform SHALL own canonical management identity、inventory、Runtime session/liveness history 和 Run correlation projection。
- Platform MAY distribute approved Robot Profile metadata in P1，但不得生成 capability verification 结论。
- Platform SHALL NOT own current motor/controller state、local watchdog、Nav2 state machine、joint control、E-stop 或 task execution transition。
- Platform outage SHALL NOT stop local execution solely because the management service is unreachable。

Go Platform 不进入第一阶段 MVP；P0 eligibility 可先使用版本化本地 fixture/config 证明 domain semantics，避免让远程同步阻塞核心需求验证。

## 12. Execution Plane Requirements

- RobotRegistry SHALL remain local execution-side operational state authority。
- 当前任务、assignment、haul phase、resource ownership 和 local heartbeat timeout SHALL 由 Fleet/execution-side components 决定。
- `RobotExecutionContext` SHALL remain vendor-neutral；AMR/Nav2 是当前真实 implementation。
- DR02、Unitree、Agibot execution context 当前均为 `NOT IMPLEMENTED`，不得从 state adapter 或 standalone command source audit 推断。
- Remote management call SHALL NOT be required to perform watchdog、cancel、safe stop 或 navigation control。

## 13. Safety / Failure Isolation

| Case | Required behavior |
| --- | --- |
| A. vendor telemetry lost | 本地 freshness 超阈值后将 robot 从 eligible set 移除；不得用 Platform 的旧 online 投影覆盖本地判断。 |
| B. vendor adapter crashes | 视为 integration Runtime liveness loss，记录 adapter/source diagnostic；不得自动恢复 `IDLE`。 |
| C. Go Platform unreachable | 本地 Fleet、Nav2、watchdog 和安全停止继续；暂停新 metadata sync，显式记录管理面缺口并 bounded-backoff。 |
| D. WMS unavailable | 不接受无法确认的新外部任务；已开始任务按本地 authority 安全继续或停止，WMS writeback 与 local execution state 分离并保留待确认状态。 |
| E. robot offline | 立即退出新任务 eligible set；沿用现有 reversible boundary，pickup 前可 requeue，pickup 后不得盲目重复分配。 |
| F. online but capability insufficient | 拒绝自动派发并返回 capability mismatch，不将 online 解释成 suitable。 |
| G. capability exists but evidence insufficient | 拒绝自动派发并返回 evidence threshold mismatch；不得把 declared/source-only claim 自动升级。 |
| H. assigned robot becomes stale/offline | assignment 前/可逆阶段允许确定性 requeue；不可逆阶段保留 ownership、告警并等待人工/专用恢复 contract。 |

## 14. Evidence / Verification Requirements

1. 每个 integration link 必须保留现有四态 evidence label 和 evidence reference。
2. 每个 capability claim 必须单独记录 maturity、环境、版本、issuer 和验证结果。
3. Simulator、mock、interface、real robot 证据不得互相替代。
4. Management heartbeat 不得证明 execution readiness；vendor telemetry 不得证明 task success。
5. Eligibility decision 必须记录使用的 Robot Profile、deployment policy 和 rejection/selection reasons。
6. 真机自动派发前必须有独立 hardware acceptance，不得由 source audit 或 simulator result 自动升级。

## 15. Scope

本需求范围包括：

- vendor-neutral robot identity/state boundary；
- capability/profile 与 evidence maturity requirements；
- task required capabilities；
- capability-aware eligibility；
- local Fleet 与 Management Plane authority/failure boundary；
- 可转成自动测试的 P0 acceptance criteria。

## 16. Non-goals

- 统一底层 motor interface 或所有 vendor SDK；
- 自研 locomotion controller、跨品牌 joint-level control；
- autonomous multi-robot cooperation 或 real-time distributed control；
- optimal robot procurement；
- production-grade cloud Fleet、OTA、统一 SLAM；
- universal ROS bridge；
- LLM task planning；
- 本轮新增 schema、API、Go integration、vendor execution context、command adapter、dashboard 或第四家 vendor。

## 17. Acceptance Criteria

### AC1 — capability match

Given `robot_01` online/idle with `payload_transport`, `robot_02` online/idle with `visual_inspection`, and a task requiring `visual_inspection`, then `robot_02` is eligible and `robot_01` is rejected with capability mismatch.

### AC2 — evidence threshold

Given `robot_02` claims `visual_inspection` at `DECLARED`, while deployment policy requires `SIM_VERIFIED`, then `robot_02` is not automatically eligible and the reason is evidence threshold mismatch.

### AC3 — vendor replacement

Given a future Vendor D adapter emits the same internal state/profile contract, Dispatcher eligibility tests require no vendor-specific branch change.

### AC4 — Platform outage

Given Go Platform becomes unreachable during local AMR execution, Nav2, local watchdog and safe-stop behavior continue; metadata sync becomes unavailable/stale without changing local task authority.

### AC5 — telemetry is not recovery

Given a robot is `OFFLINE`, when one valid vendor telemetry frame arrives, only authorized liveness fields change; business state remains `OFFLINE` until an explicit recovery gate succeeds.

### AC6 — backward-compatible haul

Given a current pickup/dropoff task with no `required_capabilities`, selection and lifecycle results match the existing deterministic Fleet baseline.

### AC7 — irreversible boundary

Given a robot becomes offline after pickup completion, the same task is not automatically reassigned to another robot and ownership remains visible for recovery.

### AC8 — liveness authority separation

Given Platform last reports a Runtime online but local vendor telemetry is stale, Dispatcher rejects the robot using local execution-side freshness; Platform online does not override it.

### AC9 — explainable rejection

Given all robots are rejected, the result lists deterministic reasons for each candidate and distinguishes state/liveness/capability/evidence/resource causes.

### AC10 — no capability guess

Given a robot has no profile or an unknown capability maturity, it is not eligible for a task requiring that capability.

## 18. Open Questions

These questions do not block the narrow P0 MVP unless explicitly stated otherwise:

- Which capability identities and constraint units belong in the first frozen taxonomy?
- Is minimum maturity global, deployment-specific, task-specific, or a constrained combination?
- Who approves a Robot Profile revision and evidence promotion in an actual organization?
- How are capability evidence expiry and software/firmware changes handled?
- Should manual override exist; if so, which gates are never overrideable?
- How should execution result semantics differ across transport, inspection and response tasks?
- At what point does Platform become the distribution authority for approved profiles rather than an aggregation consumer?
- Which real-robot acceptance suite is required before `HW_VERIFIED`?

## 19. MVP Requirement Slice

The first implementation slice should contain only:

1. versioned Robot Profile / capability representation;
2. capability evidence maturity representation with explicit provenance;
3. optional task `required_capabilities` compatible with existing haul;
4. capability/evidence filtering before existing cost selection;
5. deterministic eligibility and backward-compatibility tests.

It should not include Go Platform integration, vendor execution, real robot, dashboard, multi-robot workflow or a final universal capability taxonomy.

## 20. Requirements-driven Roadmap Proposal

| Phase | Goal | Exit boundary |
| --- | --- | --- |
| R1 — Requirements / domain model | Freeze P0 terms, authority, minimal capability/profile and task requirement contract. | Reviewed examples and rejection semantics; no runtime integration required. |
| R2 — Capability-aware Fleet | Implement local profile/task eligibility and deterministic tests while preserving haul baseline. | Eligible-set tests pass without vendor branch. |
| R3 — Management-plane integration | Define and verify Fleet-to-Platform sync/projection contract. | Platform failure isolation and stale projection behavior proven. |
| R4 — Vendor execution proof | Implement one vendor execution context at a time against simulator/official boundary. | Vendor-specific command proof and Fleet execution proof separately evidenced. |
| R5 — Real robot acceptance | Perform hardware/network/safety acceptance and evidence promotion. | Explicit robot/capability/environment acceptance, not source-derived claims. |

## 21. Authority Decisions

| Question | Requirement decision |
| --- | --- |
| Who owns current task? | Local Fleet assignment/haul lifecycle is authoritative; Platform receives a projection/history reference. |
| Who owns runtime liveness? | Local Fleet owns execution eligibility from local freshness; Platform owns management-plane Runtime liveness projection. They are different facts. |
| Who owns capability definition? | A versioned approved Robot Profile owned by Fleet/deployment configuration authority in P0; Platform may distribute/index it in P1. |
| Who owns capability verification evidence? | The validation/acceptance producer issues evidence; Platform may index references but cannot promote maturity itself. |
| Platform down? | Local execution and safety continue with last approved local profile; new management sync is unavailable and must be marked stale. |
| Fleet down? | Platform shows last observed projection as stale/offline/unknown and does not invent task completion or robot readiness. |

The governing rule is:

> Vendor determines **how** the robot is integrated. Capability determines **whether** the robot is eligible. Execution contract determines **how** a selected robot performs the task. Management Plane determines **how** the system is observed and operated.
