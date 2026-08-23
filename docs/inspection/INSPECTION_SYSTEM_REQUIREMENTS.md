# 多品牌机器人工业巡检系统需求基线

日期：`2026-08-24`

状态：**Reference Design + P0-3 Nav2/Mock Inspection SIM-VERIFIED**

适用范围：基于当前 `AMR Warehouse Navigation` 项目的 brownfield 工业巡检扩展设计

## 1. 文档定位与事实标签

本文件回答：在不推翻当前 Mock WMS、Fleet、Nav2 和 vendor integration 骨架的前提下，工业巡检业务需要增加什么需求、contract 和验收边界。

原始设计轮不修改 Fleet、Nav2、Mock WMS schema、vendor adapter、Go Platform 或 Dashboard，也不新增巡检 executor、sensor node 或 AI 模型。`2026-08-24` 后续 P0-1 只新增 `amr_warehouse_sim/inspection/` 纯 Python contract 与定向测试；上述边界保持不变。

P0-3 当前证据：在 P0-2 数据链之上，opt-in inspection executor 已复用现有 `ExecutorRuntime/RosNav2Runtime`。三组 P0 tests 共 `27 passed`，全量回归为 `162 passed, 7 skipped`；fresh headless Nav2 session 中 `candidate_dock_a` goal 返回 `SUCCEEDED`，随后 Mock sample `72 > 65` 产生 `WARNING` finding、SHA-256 evidence 与成功 report。arrival/stabilization 和 sensor 仍为 Mock；这不是真实 sensor、生产 Evidence Store、真机或现场验收。

文中统一使用以下标签：

| Label | 含义 |
| --- | --- |
| `CURRENT` | 当前仓库已有实现；具体证据成熟度仍以源码、测试或运行报告为准。 |
| `CURRENT DEMO` | 当前 Fleet 层已有纯 Python / simulated-context 行为与 pytest 证据；不是生产多车能力。 |
| `CURRENT EXPERIMENTAL` | 当前 opt-in vendor state/liveness 实验；不代表 command、巡检或真机能力。 |
| `REUSABLE` | 当前边界可保留，但需要由巡检语义扩展或组合。 |
| `PROPOSED` | 本 Reference Design 新提出的 contract 或组件。 |
| `NOT IMPLEMENTED` | 当前仓库没有对应运行路径。 |

证据标签与 capability maturity 是两条独立轴。`VERIFIED / SOURCE-AUDITED / MOCK-VERIFIED / NOT TESTED` 描述 integration link；`DECLARED / SOURCE_AUDITED / SIM_VERIFIED / HW_VERIFIED` 描述某台机器人在特定环境下的能力成熟度。二者不得互相自动升级。

## 2. Current Capability Audit

审计基线：当前 checkout `main@be00ad4c39607634db4c8b4bfb80e8f13cd09232`。审计时工作区已有未提交的 Fleet/vendor 文档改动；本文件不把这些改动误认为功能实现。`2026-08-24` 复跑 `python3 -m pytest test -q` 得到 `135 passed, 7 skipped`；本轮没有启动 live Nav2。历史 live Nav2 报告使用 `f679732`，而该提交到当前 HEAD 的 `config/task_points.yaml`、`launch/navigation.launch.py`、`config/nav2_params.yaml` 与 `maps/warehouse.yaml` 无差异。

本表的 Current capability 和 Evidence 只来自当前仓库；Go Platform 不计入本仓当前能力。

| Inspection concern | Current repo capability | Evidence | Reusable? | Gap |
| --- | --- | --- | --- | --- |
| 任务创建 | 固定点位单任务，可由 CLI 或 HTTP 创建 | [`mock_wms_db_common.py`](../../amr_warehouse_sim/mock_wms_db_common.py)、[`mock_wms_api.py`](../../amr_warehouse_sim/mock_wms_api.py) | `REUSABLE / EXTENDED` | 没有 plan、route、inspection items、capability requirement、deadline |
| 固定点位 | `map` frame 点位目录；四个业务点有 fresh-session `SUCCEEDED` 历史证据 | [`task_points.yaml`](../../config/task_points.yaml)、[固定点位矩阵报告](../wms/reports/fixed_task_points_success_matrix_regression_2026_05_15.md) | `REUSABLE / EXTENDED` | 没有 inspection view、arrival tolerance、stabilization、item acceptance |
| 导航 | 单 Gazebo AMR 的 Nav2 `NavigateToPose` 稳定基线 | [`navigation.launch.py`](../../launch/navigation.launch.py)、[HTTP executor E2E 报告](../wms/reports/mock_wms_http_executor_end_to_end_validation_2026_05_14.md) | `REUSABLE / UNCHANGED` | 不等于巡检点成功；第三方 vendor command path 未实现 |
| ready gate | 检查 5 个 lifecycle node、`map -> odom` 和 action server | [`mock_wms_executor.py`](../../amr_warehouse_sim/mock_wms_executor.py)、[ready-gate 报告](../wms/reports/headless_nav2_ready_integration_validation_2026_05_15.md) | `REUSABLE / EXTENDED` | 只证明 Nav2 prerequisite，不证明 sensor、safety 或 inspection ready |
| 状态回写 | SQLite/HTTP 回写五态与 `status_reason` | [`mock_wms_db_common.py`](../../amr_warehouse_sim/mock_wms_db_common.py)、HTTP/executor tests | `REUSABLE / EXTENDED` | 当前 `succeeded` 直接等于导航成功，没有 point/run result 层 |
| Fleet Dispatcher | 先检查 `IDLE + fresh heartbeat + no active task`，再按静态站点 cost 选择 | [`dispatcher.py`](../../amr_warehouse_sim/fleet/dispatcher.py)、dispatcher tests | `CURRENT DEMO / EXTENDED` | 没有 capability、evidence threshold、inspection policy eligibility |
| Robot Registry | demo robots、state、task、station、heartbeat、battery 与可选 SQLite | [`registry.py`](../../amr_warehouse_sim/fleet/registry.py)、registry tests | `CURRENT DEMO / EXTENDED` | 没有 Robot Profile、sensor inventory、capability snapshot |
| heartbeat | 本地 freshness 检查与 timeout sweep | [`registry.py`](../../amr_warehouse_sim/fleet/registry.py)、[`heartbeat.py`](../../amr_warehouse_sim/fleet/heartbeat.py) | `CURRENT DEMO / EXTENDED` | telemetry freshness、execution readiness、business availability、safety readiness 尚未分开 |
| offline | stale robot 可进入 `OFFLINE` | heartbeat/registry tests | `CURRENT DEMO / EXTENDED` | vendor adapter liveness 与 execution runtime liveness 需要明确 source |
| reassignment | pickup 前可 requeue/reassign；pickup 后阻止 demo-level reassign | [`heartbeat.py`](../../amr_warehouse_sim/fleet/heartbeat.py)、haul/heartbeat tests | `CURRENT DEMO / EXTENDED` | 没有 point checkpoint、partial evidence、inspection resumption policy |
| resource lock | FIFO acquire/release/timeout 与 ordered acquire | [`resources.py`](../../amr_warehouse_sim/fleet/resources.py)、resource tests | `CURRENT DEMO / EXTENDED` | 尚未接入 haul path；不是 traffic management |
| vendor adapter | 三家 opt-in、state-only adapter 统一到 heartbeat | [`integrations/`](../../amr_warehouse_sim/integrations)、[multi-vendor architecture](../fleet/MULTI_VENDOR_ARCHITECTURE.md) | `CURRENT EXPERIMENTAL / EXTENDED` | command/inspection path 均未实现；三家 evidence maturity 不同 |
| execution abstraction | `RobotExecutionContext` 只有 ready + navigate；Fleet 默认 simulated context | [`execution_context.py`](../../amr_warehouse_sim/fleet/execution_context.py)、execution-context tests | `CURRENT DEMO / EXTENDED` | 无 arrival、inspect、acquire、validate、evaluate、cancel contract |
| HTTP API | health/create/list/get/status patch | [`mock_wms_api.py`](../../amr_warehouse_sim/mock_wms_api.py)、HTTP tests/report | `REUSABLE / EXTENDED` | 无 inspection plan/run/point/evidence/finding API |
| SQLite | Mock WMS 与 Fleet 本地 metadata 持久化 | Mock WMS/Fleet source and tests | `REUSABLE / EXTENDED` | 无 inspection schema；不应存大体积 artifact blob |
| evidence / reports | 自动化测试、live Nav2、WMS 与 vendor 分层报告 | [`test/`](../../test)、[`docs/reports/`](../reports)、[`docs/wms/reports/`](../wms/reports)、[`docs/fleet/`](../fleet) | `REUSABLE / EXTENDED` | 不是运行时 Inspection Evidence Store 或自动报告 |
| management plane | 本仓没有 client/sync/runtime path | [Heterogeneous Fleet Context](../fleet/HETEROGENEOUS_FLEET_SYSTEM_CONTEXT.md) 明确标注 AMR 与 Platform 未集成 | 当前不可复用；只可参考边界 | 需要未来异步 projection contract |
| sensor acquisition | 只有导航所需 `/scan`、odom、TF 仿真链 | launch、system architecture、Nav2 reports | 对巡检 `NO` | 无 RGB、thermal、audio、gas、gauge acquisition contract |
| inspection action | 无 | 当前源码无相应模块 | `NEW` | capture/measure/dwell/stabilize/acceptance 均待设计 |
| anomaly detection | 无 | 当前源码无 rule/CV/ML evaluator | `NEW` | 需要 rule/classical/ML 分层 |
| alarm | 无巡检 alarm；Fleet 只有结构化 event/error | `FleetEvent`、`ResourceEvent` | `NEW` | system/execution fault 与 inspection finding 必须分开 |
| inspection report | 无 | 当前只有人工编写的验证报告 | `NEW` | 需要 run/point/result/evidence 可追溯聚合 |

### 2.1 审计结论

当前可直接保留的主干是：

```text
Task intake
-> readiness prerequisite
-> navigation
-> result writeback
```

当前可扩展的调度骨架是：

```text
Robot Registry
-> Fleet eligibility
-> assignment
-> execution context
-> heartbeat/offline/reassignment
-> resource ownership
```

巡检新增主干是：

```text
arrival acceptance
-> inspection action
-> sensor acquisition
-> data quality
-> evaluation
-> evidence
-> finding/alarm/report
```

三家 vendor 当前只支撑 state/liveness integration 的设计讨论，不支撑“已经执行巡检”的事实陈述。

## 3. Background 与 Problem

### 3.1 Reference scenario

某工业园区在不同项目时期已经引入不同来源的移动机器人。园区希望在保留各机器人真实 transport、控制和安全边界的前提下，统一管理周期巡检和异常复核任务。

这是 brownfield reference scenario，不代表真实客户，也不说明 DEEPRobotics DR02 Pro、Unitree Go2、Agibot D1 MaxPro 是最优采购组合或已经完成巡检任务。

### 3.2 Problem statement

当前系统能创建固定点任务、通过 ready gate 调用 Nav2、记录结果，并在 demo Fleet 层完成注册、分配、心跳、取货前重分配和资源锁。但巡检任务不是“多导航几个点”：它必须证明机器人在正确位置、传感器与数据有效、巡检规则得到执行、结果和证据可追溯。

系统需要在以下边界下把巡检业务自然加到当前骨架上：

1. 不把 `NavigateToPose SUCCEEDED` 当作 inspection point success；
2. 不把 telemetry arrival 当作 execution readiness；
3. 不把 robot online 当作 inspection capability；
4. 不把 vendor support 当作 capability qualification；
5. 不让 Management Plane 进入本地 safety/control loop；
6. 不按 vendor name 硬编码 Dispatcher；
7. 不让巡检 execution phase 污染 business task status。

## 4. Actors

| Actor | 需求与边界 |
| --- | --- |
| Operations operator | 创建/查看计划和任务、处理 finding、请求异常复核；不直接拥有机器人控制状态。 |
| Inspection planner | 定义 route、point、inspection item、频率、优先级和 acceptance policy。 |
| Fleet administrator | 批准 Robot Profile、capability policy、resource policy 和 deployment scope。 |
| Robot integration engineer | 隔离 vendor SDK/transport，提供 state 与未来 command contract 的证据。 |
| Inspection integration engineer | 定义 sensor/action/quality/evaluation contract，不把 vendor schema泄漏到业务层。 |
| Maintenance engineer | 区分 robot、sensor、runtime、adapter、network 与 inspected asset fault。 |
| Local robot runtime | 执行 readiness、navigation、inspection action、watchdog 和 local safe stop。 |
| Task/plan service | 产生业务任务并消费 coarse result/writeback；不发底层 command。 |
| Management Plane | 未来聚合 identity、runtime liveness、run metadata 和 artifact reference；不参与实时控制。 |
| Evidence consumer / auditor | 按 robot、point、time、observation、evaluation 和 provenance 复核结果。 |

## 5. Use Cases

### UC-01 周期巡检

Operator 激活 Inspection Plan，系统生成一个 Inspection Task/Run，按 route 顺序到达多个 point，执行配置的 inspection items，最终产生一份 run report。

### UC-02 异常复核

已有 finding 触发一个高优先级复核任务。复核任务可以复用已有 route/point，但必须生成新的 run、timestamp、observation 和 evaluation，不覆盖原证据。

### UC-03 单点重试

某点因 sensor unavailable 或 data invalid 失败。系统按 policy 在同一 robot 上做 bounded retry；若仍失败，记录 point failure 和 system fault，任务可选择 partial completion 或整体 failure。

### UC-04 取点前掉线重分配

机器人在尚未产生不可替代 point evidence 前掉线，assignment 可 release，并由另一个满足相同 capability/evidence/resource policy 的机器人重分配。已产生的 evidence 不删除。

### UC-05 巡检中掉线

机器人在 acquisition 中掉线。当前 attempt 终止并标记 evidence completeness；只有在 task policy、point idempotency 和 capability 都允许时才从该 point 重新开始，不能把半帧或 stale sample 当作成功。

### UC-06 Platform 不可达

本地安全与当前已接受的执行按 local policy 继续或安全停止；management projection 出现 gap/stale。不得因 Platform timeout 阻塞 E-stop、watchdog、Nav2 或 local threshold alarm。

## 6. Architecture Invariants

### INV-01 Navigation success != Inspection point success

`NavigateToPose SUCCEEDED` 只证明 Nav2 对 goal 给出成功终态。point 只有在 arrival tolerance、stabilization、inspection action、data quality、evaluation 和 evidence persistence 全部满足 point policy 后才可成功。

### INV-02 Telemetry received != Robot ready

一帧 `/JOINTS_DATA`、`/lowstate` 或 Agibot JSONL event 只证明对应 transport path 有观测。它不能自动恢复 `OFFLINE -> IDLE`，也不能证明 task、sensor、safety 或 command path ready。

### INV-03 Robot online != Inspection capable

online 是 freshness/liveness 事实。inspection eligibility 还需要 required capability match、capability evidence threshold、resource availability、business state 和 local ready gate。

### INV-04 Vendor determines HOW; capability determines WHETHER

Vendor 决定 SDK、topic、DDS、TCP、ABI 和 command implementation 如何接入；capability/evidence policy 决定机器人是否有资格执行任务。Dispatcher 不出现 `if vendor == ...`。

### INV-05 Platform availability != Local safety availability

Management Plane 不拥有 `/cmd_vel`、joint command、E-stop、watchdog 或 local safe stop。Platform 离线会损失全局查询/关联能力，但不得破坏本地安全闭环。

### INV-06 Business, assignment and execution state remain separate

业务方只消费任务粗状态；Fleet 维护 robot-task binding；execution 维护 point 内细阶段。任何一套状态都不能覆盖另外两套事实。

## 7. Functional Requirements

### 7.1 Plan / Task / Route

| ID | Requirement |
| --- | --- |
| `FR-PLAN-01` | 系统 SHALL 表示 `InspectionPlan`，至少引用 schedule/policy、route、priority 和 task template；schedule engine 可晚于 MVP。 |
| `FR-PLAN-02` | 每次 plan 触发 SHALL 创建新的 `InspectionTask` 和 `InspectionRun` identity，不覆盖历史 run。 |
| `FR-TASK-01` | `InspectionTask` SHALL 包含 task identity、route、priority、required capabilities、deadline/policy 和 ordered points。 |
| `FR-TASK-02` | `InspectionPoint` SHALL 包含 pose、arrival policy、stabilization requirement、inspection items 和 point acceptance policy。 |
| `FR-TASK-03` | `InspectionItem` SHALL 使用 vendor-neutral item kind，例如 `rgb / thermal / audio / gas / gauge_reading`；这些只是 reference capability，不代表当前机器人具备相应 sensor。 |
| `FR-TASK-04` | Multi-point route SHALL 归属于同一个 `InspectionRun`，不得默认拆成多个互不关联的 haul task。 |
| `FR-TASK-05` | Task/point/item contract 版本 SHALL 被 run snapshot 引用，使历史结果不被后续配置变更重解释。 |

### 7.2 Fleet eligibility 与 assignment

| ID | Requirement |
| --- | --- |
| `FR-FLEET-01` | Dispatcher SHALL 先形成 eligible set，再计算 cost。 |
| `FR-FLEET-02` | Eligibility 至少要求：registered、local heartbeat valid、business state allowed、no active task conflict、required capability match、capability evidence sufficient、resource available。 |
| `FR-FLEET-03` | Dispatcher SHALL NOT 依据 vendor name 分支。 |
| `FR-FLEET-04` | 每个 rejection SHALL 有确定性的 reason code，至少区分 liveness、state、capability mismatch、evidence insufficient、resource conflict。 |
| `FR-FLEET-05` | Profile、capability evidence 或 task requirement 缺失/不可解析时 SHALL fail closed。 |
| `FR-FLEET-06` | Assignment SHALL 保存本次决策使用的 profile/policy snapshot reference 和 cost reason。 |
| `FR-FLEET-07` | 现有 haul task 在没有 inspection requirement 时 SHALL 保持原行为；本设计不反向修改当前 baseline。 |

### 7.3 Robot execution 与 arrival

| ID | Requirement |
| --- | --- |
| `FR-EXEC-01` | Robot execution SHALL 保留 current ready gate 和 `NavigateToPose` abstraction。 |
| `FR-EXEC-02` | Navigation result SHALL 先进入 `ARRIVED` candidate，再由 arrival tolerance/pose freshness 检查确认；不得直接完成 point。 |
| `FR-EXEC-03` | Arrival confirmation 后 SHALL 执行 stabilization policy，再开始 acquisition。 |
| `FR-EXEC-04` | Robot navigation/readiness 与 inspection action SHALL 使用可组合的窄 contract；本设计不要求把两者强行合并为一个 vendor base class。 |
| `FR-EXEC-05` | timeout、cancel、retry 和 shutdown SHALL 明确当前 owner，并产生可关联的 execution result。 |
| `FR-EXEC-06` | 在 lost communication 或 stale command 情况下，local runtime SHALL 进入 vendor/local safety contract 定义的 safe behavior；Platform 不参与该判定。 |

### 7.4 Inspection action / sensor / quality

| ID | Requirement |
| --- | --- |
| `FR-INSP-01` | `InspectionActionContext` SHALL 接受 point/item/action context，并返回 observation references 与 action result；不携带 Fleet dispatch logic。 |
| `FR-INSP-02` | 每个 observation SHALL 包含 source、capture time、received time、robot、point、sensor/device、frame/calibration version（若适用）和 artifact reference。 |
| `FR-INSP-03` | Data Quality Gate SHALL 在 evaluation 前检查 freshness、completeness、schema、range、frame/pose association 和 item-specific quality。 |
| `FR-INSP-04` | stale、partial、malformed 或 provenance 不明的数据 SHALL NOT 进入 point success。 |
| `FR-INSP-05` | Sensor unavailable 与 inspected asset anomaly SHALL 使用不同的对象和 reason namespace。 |
| `FR-INSP-06` | 同一 point 的 retry SHALL 产生新 attempt identity；不得覆盖失败 observation。 |

### 7.5 Evaluation / finding / alarm

| ID | Requirement |
| --- | --- |
| `FR-EVAL-01` | Evaluation SHALL 支持 deterministic rule、classical signal/CV 和 ML/AI 三类 evaluator，并记录 evaluator identity/version。 |
| `FR-EVAL-02` | 安全关键阈值 SHALL 能在 edge/local path 上独立工作，不得完全依赖 cloud AI。 |
| `FR-EVAL-03` | Raw data、Observation、Evaluation、Finding 和 Alarm SHALL 是不同对象，保留各自 provenance 与 lifecycle。 |
| `FR-EVAL-04` | `InspectionFinding` SHALL 表示被检对象的正常/异常判定；`SystemFault` SHALL 表示 robot/sensor/runtime/execution 故障。 |
| `FR-ALARM-01` | Alarm severity SHALL 至少支持 `INFO / WARNING / CRITICAL`，并允许 deployment policy 对 finding 进行映射。正常结果不是 alarm。 |
| `FR-ALARM-02` | Alarm SHALL 引用 finding 和 evidence；system fault notification SHALL 引用 fault，不得伪装成设备异常。 |
| `FR-ALARM-03` | ML confidence SHALL NOT 替代 severity、data quality 或 deterministic safety threshold。 |

### 7.6 Evidence / report

| ID | Requirement |
| --- | --- |
| `FR-EVID-01` | 每个 point result SHALL 可追溯到 run、task、robot、point、time、pose、items、observation、quality、evaluation 和 evidence provenance。 |
| `FR-EVID-02` | Metadata DB SHALL 保存结构化索引和状态；图片、音频、热图等 artifact SHALL 通过 URI/hash/reference 关联，不直接作为 blob 塞入当前 SQLite。 |
| `FR-EVID-03` | Evidence persistence 成功是 point acceptance 的显式 gate；仅 evaluation 完成不等于 evidence 已安全保存。 |
| `FR-EVID-04` | Inspection Report SHALL 聚合 point result、finding、fault、retry、skipped/partial reason 和 artifact reference。 |
| `FR-EVID-05` | 报告 SHALL 区分 task success、partial success 和 failed；不能隐藏 point failure。 |

### 7.7 Management Plane

| ID | Requirement |
| --- | --- |
| `FR-MGMT-01` | 未来 Management Plane 可聚合 Robot、Device、Runtime、RuntimeSession、RuntimeHeartbeat 和 Run envelope。 |
| `FR-MGMT-02` | `InspectionRun` 可映射到 Platform `Run` 的 correlation envelope，但 point result、evaluation truth 和 artifact content 仍由 inspection domain/evidence producer 拥有。 |
| `FR-MGMT-03` | Fleet/inspection runtime 与 Platform SHALL 通过显式异步 projection/sync contract 交互，第一阶段不得共享数据库。 |
| `FR-MGMT-04` | Platform projection SHALL 带 source timestamp、received timestamp 和 staleness；不得覆盖 local current task、readiness 或 final domain result。 |
| `FR-MGMT-05` | Platform 不可达时，本地 execution/safety SHALL 继续按 local policy 工作；同步 gap 必须可见。 |
| `FR-MGMT-06` | Dashboard 未来只消费 Management Plane/domain projection，不成为 canonical control or result owner。 |

## 8. Non-functional Requirements

| ID | Quality | Requirement |
| --- | --- | --- |
| `NFR-01` | Safety | E-stop、watchdog、command ownership、safe stop、local threshold 不得依赖远端 Platform。 |
| `NFR-02` | Failure isolation | 单一 vendor adapter、sensor、evaluator、WMS API 或 Platform 故障不得让无关本地 safety loop 失效。 |
| `NFR-03` | Traceability | 每个 eligibility、assignment、action、observation、evaluation、finding、fault 和 report 记录 SHALL 有 correlation identity、timestamp、source/version。 |
| `NFR-04` | Determinism | MVP 的 eligibility、rule evaluation、retry 和 state transition SHALL 可用 fixed clock/input/context 做确定性测试。 |
| `NFR-05` | Idempotency | 外部重复 create/writeback、point retry 和 projection retry SHALL 有明确 idempotency/correlation policy。 |
| `NFR-06` | Data integrity | Metadata 与 artifact reference SHALL fail closed；hash/provenance 缺失不得被标成完整 evidence。 |
| `NFR-07` | Replaceability | 等价 capability 的新 vendor integration 不应修改 Dispatcher business branch。 |
| `NFR-08` | Backward compatibility | 当前 Nav2、Mock WMS、Fleet Stage 1–5、vendor state-only tests SHALL 不因未来巡检扩展而改变默认行为。 |
| `NFR-09` | Observability | current fact、projection、stale fact 和 historical evidence SHALL 在 API/UI 中可区分。 |
| `NFR-10` | Bounded behavior | retry、buffer、queue 和 remote call SHALL 有上限；不得阻塞 local control/safety loop。 |
| `NFR-11` | Security | 真正进入现场前，task/action/evidence API SHALL 有身份、授权、传输保护和审计；本轮不设计具体 IAM。 |
| `NFR-12` | Deployability | 首个 vertical slice SHALL 不要求真实 thermal camera、AI、三家 vendor runtime 或多车 Gazebo。 |

## 9. Proposed Contract Model

以下 YAML 只是 contract illustration，不是当前 schema 或可执行配置。

```yaml
inspection_plan:
  plan_id: plan-example-001
  route_id: route-example-001
  schedule_policy_ref: periodic-policy-v1
  task_template_version: inspection-task-v1

inspection_task:
  task_id: inspection-task-example-001
  route_id: route-example-001
  priority: normal
  required_capabilities:
    - identity: mobile
      minimum_maturity: SIM_VERIFIED
    - identity: visual_inspection
      minimum_maturity: SIM_VERIFIED
  deadline:
    complete_before: "example-only"
    on_miss: fail_or_operator_review
  points:
    - point_id: point-a
      pose:
        frame_id: map
        x: 1.0
        y: 2.0
        yaw: 0.0
      arrival_policy:
        position_tolerance_m: 0.20
        yaw_tolerance_rad: 0.20
        pose_max_age_ms: 500
      stabilization:
        dwell_ms: 1000
        motion_below_threshold_required: true
      inspection_items:
        - item_id: item-a-rgb
          kind: rgb
          action: capture
          quality_policy_ref: rgb-quality-v1
          evaluation_policy_ref: visual-rule-v1
      acceptance_policy:
        require_all_items: true
        require_evidence_persisted: true
        max_attempts: 2
```

示例中的数值不是当前项目验收参数，也不说明现有机器人具备 RGB sensor。真实值必须由传感器、地图、现场安全与 acceptance experiment 冻结。

### 9.1 InspectionRun 与 point attempt

```text
InspectionTask
  -> InspectionRun (one execution attempt for the task)
       -> PointExecution[ordered]
            -> PointAttempt[1..N]
                 -> Observation[0..N]
                 -> QualityResult
                 -> EvaluationResult
                 -> Finding[0..N]
                 -> ArtifactReference[0..N]
```

`InspectionRun` 不是三个独立 haul task 的拼接。Point retry 产生新的 `PointAttempt`，并保留先前失败 evidence。

## 10. Capability Requirements

### 10.1 Capability record

概念上至少需要：

```text
capability identity
+ qualifiers / constraints
+ claim source
+ maturity
+ evidence reference
+ robot/profile/software/environment scope
+ validity/review state
```

`mobile`、`visual_inspection`、`thermal_inspection`、`audio_inspection`、`gas_measurement` 只是 seed vocabulary，不绑定任何 vendor。

### 10.2 两条 evidence 轴

| Axis | Values | 回答的问题 |
| --- | --- | --- |
| Integration evidence | `VERIFIED / SOURCE-AUDITED / MOCK-VERIFIED / NOT TESTED` | SDK/transport/adapter/IPC 这条 link 有什么证据？ |
| Capability maturity | `DECLARED / SOURCE_AUDITED / SIM_VERIFIED / HW_VERIFIED` | 某 robot/profile 在什么环境中证明了什么业务能力？ |

例如，Go2 telemetry adapter 的 source audit 不能证明 `visual_inspection=HW_VERIFIED`；DR02 MuJoCo state telemetry runtime verified 也不能证明它已经完成巡检任务。

### 10.3 Eligibility order

```text
registered identity
AND local liveness usable
AND business state allowed
AND no active task conflict
AND required capability present
AND capability maturity >= deployment policy
AND resource available
THEN compute cost
```

priority 或 distance 只能在 eligible set 内排序，不能绕过 safety/evidence gate。

## 11. Failure Handling Requirements

详细处置矩阵见 [Inspection System Architecture](./INSPECTION_SYSTEM_ARCHITECTURE.md)。需求层冻结以下原则：

1. retry 必须 bounded，且每次产生 attempt identity；
2. reassignment 只在任务/point 的可逆边界允许；
3. 已产生 evidence 不删除、不覆盖；
4. anomaly detected 是业务 finding，不是 execution failure；
5. sensor unavailable/data invalid 是 system/execution fault，不是 inspected asset anomaly；
6. capability mismatch/evidence insufficient 在 dispatch 前 fail closed；
7. Platform/WMS unreachable 不阻塞 local safety；
8. resource occupied 保持等待或重新调度，不伪造成 navigation failure。

## 12. Safety Requirements

巡检设计必须明确四种不同事实：

| Concern | 事实拥有者 | 不能推出 |
| --- | --- | --- |
| Communication liveness | adapter/runtime freshness source | execution ready、sensor ready、safe |
| Business availability | Fleet/Registry/task policy | local controller healthy、capability verified |
| Execution readiness | local RobotExecution/InspectionAction contexts | task completed、finding normal |
| Safety readiness | local robot/vendor safety chain | Platform online、report complete |

进入真实机器人前必须另行定义 command owner、E-stop owner、watchdog、lost communication、stale data、safe stop、resume authority 和 hardware acceptance。本 Reference Design 不声称 functional safety 或现场安全认证。

## 13. Evidence Model

每个 point result 至少需要：

```text
inspection_run_id
task_id
robot_id
point_id
point_attempt_id
capture/evaluation timestamps
arrival pose + pose source/freshness
inspection items
artifact references + hashes
data quality result
evaluation result
finding/severity/confidence/reason
system faults
producer/runtime/profile/policy versions
evidence provenance
```

推荐存储分层：

```text
Metadata DB
  structured identity/state/index/reference

Artifact Store
  image/audio/thermal/log payload

Report
  immutable references + human-readable aggregation
```

当前不实现 object storage；MVP 可用本地受控 artifact directory 加 hash/reference 验证 contract，但不能把它宣传为生产 Evidence Store。

## 14. Current vs Proposed

| Capability | Current | Reuse | Proposed |
| --- | --- | --- | --- |
| Nav2 navigation | `CURRENT`：单 Gazebo AMR 有 live report | `UNCHANGED` | 作为 point navigation prerequisite |
| fixed task points | `CURRENT`：四点 fresh-session success matrix | `EXTENDED` | 增加 arrival/view/stabilization/item policy |
| Mock WMS task | `CURRENT`：single target + five states | `EXTENDED` | InspectionPlan/Task/Route/Run contracts；不改当前 schema |
| ready gate | `CURRENT`：Nav2 lifecycle/TF/action | `EXTENDED` | navigation + inspection + safety readiness 分层 |
| status writeback | `CURRENT`：SQLite/HTTP coarse status | `EXTENDED` | task/run/point/fault/finding 独立结果 |
| Robot Registry | `CURRENT DEMO` | `EXTENDED` | approved profile、capability/evidence snapshot |
| Fleet Dispatcher | `CURRENT DEMO`：availability + static cost | `EXTENDED` | capability/evidence/resource eligibility before cost |
| heartbeat/offline | `CURRENT DEMO` | `EXTENDED` | provenance-aware local liveness 与 point recovery |
| reassignment | `CURRENT DEMO`：pickup 前 | `EXTENDED` | point 可逆边界与 partial evidence policy |
| resource lock | `CURRENT DEMO`，尚未接 haul | `EXTENDED` | zone/corridor/charging/equipment access resources |
| RobotExecutionContext | `CURRENT DEMO`：ready + navigate | `EXTENDED` | 保持窄接口，与 InspectionActionContext 组合 |
| vendor state adapters | `CURRENT EXPERIMENTAL`：liveness only | `EXTENDED` | 仍只作为 state plane；command path separately qualified |
| vendor command execution | `NOT IMPLEMENTED` | — | future per-vendor execution context |
| sensor acquisition | `CURRENT MOCK`：fixed reading sequence | pattern only | 真实 InspectionAction/Sensor adapters 仍未实现 |
| data quality | `CURRENT MOCK`：provenance/freshness/completeness gate | `EXTENDED` | item-specific range/frame/pose policy |
| anomaly evaluation | `CURRENT MOCK`：versioned maximum-threshold rule | `EXTENDED` | classical/ML evaluators 仍未实现 |
| evidence persistence | `CURRENT MOCK`：本地 JSON + SHA-256 reference | pattern only | metadata DB/object store 仍未实现 |
| alarm/report | `CURRENT MOCK`：单点 success/finding/fault/retry/artifact report；无 alarm | `EXTENDED` | multi-point/partial report 与 alarm projection |
| Management Plane | AMR `NOT INTEGRATED` | concept only | future async Robot/Runtime/Run projection |
| Dashboard | `NOT INTEGRATED` | none current | future operator view only |

## 15. Future MVP and Phases

### Phase 1 — minimal vertical slice

```text
Operator
-> create one inspection task
-> one current AMR point
-> existing ready gate + NavigateToPose
-> explicit arrival acceptance
-> mock inspection sample
-> deterministic threshold rule
-> metadata + artifact reference
-> point result + report
```

P0-3 已把该数据链接到现有单车 Nav2 runtime，并在 fresh headless simulation 中完成一次 `candidate_dock_a` goal。`temperature=72`、threshold `65` 产生 `WARNING` finding，同时在 evidence gate 后完成 point。arrival/stabilization、sensor acquisition 仍为 Mock，生产持久化后端仍未实现。

### Phase 2 — multi-point run

一个 `InspectionRun` 顺序执行 A/B/C point，每点独立 action、quality、evaluation 和 evidence；支持 bounded point retry 与 partial report。

### Phase 3 — capability-aware Fleet

用固定 profiles、fixed policy、fake context 和 deterministic tests 验证 `required_capabilities + maturity threshold`，仍不直接连接 vendor runtime。

### Phase 4 — real integrations

一次只推进一个 vendor execution context 或一种真实 sensor；分别记录 simulator command proof、Fleet execution proof、real hardware acceptance。之后才考虑 Go Platform、Dashboard 和 historical analytics。

## 16. Acceptance Criteria

### 16.1 本轮设计文档验收

| AC | Pass condition |
| --- | --- |
| `AC1` | 能从现有 Mock WMS / Fleet / Nav2 明确映射到巡检系统。 |
| `AC2` | 全文区分 `CURRENT / PROPOSED / NOT IMPLEMENTED`。 |
| `AC3` | 不把 vendor telemetry 解释成 inspection capability。 |
| `AC4` | 不把 Navigate success 解释成 Inspection success。 |
| `AC5` | 不让 Platform 进入 local safety/control loop。 |
| `AC6` | Dispatcher 不按 vendor name 分支。 |
| `AC7` | 结果具备 robot、point、time、observation、evaluation、evidence 追溯链。 |

### 16.2 未来 MVP 验收建议

1. 同一个 navigation success 输入可分别得到 point success、data-invalid failure 和 anomaly finding，证明状态没有混合；
2. point 只有 evidence persistence 完成后才成功；
3. fake sensor stale/invalid 时不得进入 evaluator success；
4. capability mismatch 与 evidence insufficient 都在 dispatch 前确定性拒绝；
5. Platform/WMS 模拟不可达时，本地 safety path 不等待远端；
6. retry 保留两个 point attempt 和各自 evidence；
7. report 能列出 success、finding、system fault、retry 与 artifact reference；
8. 当前 `python3 -m pytest test -q` baseline 不回归。

## 17. Non-goals

- 不把仓库改名为 Inspection System；
- 不实现巡检 executor、sensor node、CV/AI model 或 capability dispatcher；
- 不修改 Mock WMS schema、Fleet、Nav2、vendor adapters；
- 不连接 Go Platform 或 Dashboard；
- 不证明 DR02、Go2、D1 MaxPro 已完成巡检；
- 不做 procurement recommendation；
- 不做完整 traffic management、HA cluster、cloud platform、IAM 或 production object storage；
- 不声称 real robot、现场安全、functional safety 或生产验收。

## 18. Related Documents

- [Inspection System Architecture](./INSPECTION_SYSTEM_ARCHITECTURE.md)
- [Inspection System Interview Guide](./INSPECTION_SYSTEM_INTERVIEW_GUIDE.md)
- [Fleet / EMS Design](../fleet/EMS_FLEET_DESIGN.md)
- [Task Lifecycle](../fleet/TASK_LIFECYCLE.md)
- [Resource Locking](../fleet/RESOURCE_LOCKING.md)
- [Multi-Vendor Architecture](../fleet/MULTI_VENDOR_ARCHITECTURE.md)
- [Vendor Validation Report](../fleet/VENDOR_VALIDATION_REPORT.md)
- [Mock WMS PRD](../prd_mock_wms_task_flow.md)
