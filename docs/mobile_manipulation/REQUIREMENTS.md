# Mobile Manipulation V1 Requirements

日期：`2026-08-27`

状态：**REQUIREMENTS BASELINE / IMPLEMENTATION NOT STARTED**

## 1. 规范用语

- `必须`：V1 acceptance 的强制条件。
- `应`：默认要求；若偏离，必须有记录的 architecture decision 与等价验收。
- `不得`：禁止行为或禁止 claim。
- `DEMO THRESHOLD`：只用于当前 simulation demonstration 的经验参数，不是工业标准或安全限值。

每条 requirement 都必须由 [ACCEPTANCE_PLAN.md](./ACCEPTANCE_PLAN.md) 中的 test/evidence 证明。文档 review、源码存在、pytest、Gazebo runtime 与真实硬件是不同证据层。

## 2. Baseline 与范围

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-001 | Mobile Manipulation 必须使用独立 opt-in launch/model/world/config，不得改变现有 `navigation.launch.py` 默认行为。 | baseline file hash + launch graph comparison | 0–1 |
| MM-REQ-002 | 现有 AMR test suite 必须在每个 Gate 合入前回归通过；已有失败不得被删除或降级掩盖。 | pytest/colcon result | 0–7 |
| MM-REQ-003 | V1 必须保持 single robot、single arm、single active task；Fleet 多机器人不得进入实现范围。 | config/static test + runtime graph | 0–7 |
| MM-REQ-004 | V1 系统仿真必须使用 ROS 2 Jazzy + Gazebo Harmonic；不得引入 Isaac Sim 或 MuJoCo runtime。 | dependency manifest + process inventory | 0–7 |
| MM-REQ-005 | 第三方 core 必须通过 package dependency、xacro include 或 adapter 使用；不得无来源复制大量 upstream code。 | provenance manifest + diff review | 0–1 |
| MM-REQ-006 | 任何 simulation result 都不得表述为真机、Sim2Real、工业生产或功能安全认证。 | report/README claim audit | 0–7 |

## 3. Task 与 Mission

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-010 | 系统必须定义 `WorkcellTask`，至少包含 task identity、pickup/work station、dropoff station、target object、operation、validity/deadline 与 business status。 | schema contract test | 0 |
| MM-REQ-011 | 每次执行必须生成不可复用的 `execution_id`；每个 child action 必须有 `command_id` 和 attempt identity。 | unit/integration test | 4 |
| MM-REQ-012 | Mission Manager 必须是 Mission phase 的唯一 writer，并拒绝未定义 transition。 | FSM unit test | 4 |
| MM-REQ-013 | WMS business status、Mission execution phase、child action state 和 Robot State 必须分离，不能共用一个 bool/status 字段。 | schema/static + transition tests | 4 |
| MM-REQ-014 | 过期、尚未生效、字段缺失或 operation unsupported 的 task 必须在任何 motion 前拒绝。 | invalid-task tests | 4 |
| MM-REQ-015 | V1 同一 robot 同时最多执行一个 WorkcellTask；重复/并发 claim 必须 fail closed。 | concurrent claim/admission test | 4 |
| MM-REQ-016 | Task `SUCCESS` 必须满足 PRD 的完整 success predicate，包括 evidence persisted 与无 unresolved active command。 | end-to-end assertion | 6 |
| MM-REQ-017 | Mission 不得从 planner/controller/raw sensor callback直接跳过 adapter contract 推进状态。 | dependency/static architecture test | 4 |
| MM-REQ-018 | deadline/timeout 必须使用 absolute deadline或明确 budget传播到 child command，不能每层重置为全新无限预算。 | clock-controlled unit test | 4 |

## 4. Navigation Interface

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-020 | Mission 必须只通过 Navigation Interface 调用 navigation，不直接依赖 Nav2 BT、planner/controller plugin 或 `/cmd_vel`。 | dependency/static test | 4 |
| MM-REQ-021 | Navigation Adapter 必须把高层 station/staging target 映射为 Nav2 `NavigateToPose`，并保留 goal/command correlation。 | adapter integration test | 2–4 |
| MM-REQ-022 | Navigation result 必须区分 `SUCCESS / FAILED / CANCELED / TIMEOUT`，并保留 underlying Nav2 result/status。 | result mapping tests | 4 |
| MM-REQ-023 | 发送 goal 前必须通过 lifecycle、`map -> odom`、Action server、fresh state 和 Interlock admission ready gate。 | ready-gate fault tests | 2–4 |
| MM-REQ-024 | 当 ArmState 不是 fresh `STOWED` 时，Navigation Adapter 必须拒绝 admission，且不得发送 Nav2 goal。 | mandatory fault case 2 | 4/7 |
| MM-REQ-025 | Nav2 `SUCCESS` 只能触发 `WAIT_BASE_STATIONARY_*`，不得直接触发 perception/manipulation。 | FSM integration test | 4 |
| MM-REQ-026 | Navigation cancel 必须传播到 active Nav2 goal，并区分 cancel requested、accepted、terminal Action state和physical stop confirmation。 | cancel integration/fault test | 4/7 |
| MM-REQ-027 | Navigation timeout 后必须发起 cancel/stop；未确认停止时必须返回 stop-unconfirmed fault，不得释放 ownership。 | timeout fault injection | 7 |
| MM-REQ-028 | Station A/B staging pose 必须针对新 robot footprint、camera view、arm reach与collision重新验证；旧固定点成功不能直接复用为 Gate 2 证据。 | runtime pose/reachability report | 2–3 |
| MM-REQ-029 | Mission、Manipulation 或 WMS 不得直接发布 base `/cmd_vel`。 | ROS graph/static test | 2–7 |

## 5. Manipulation Interface

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-030 | Mission 必须只通过 Manipulation Interface 请求 `scan/pick/place/stow/cancel-or-stop/state`。 | interface/static test | 3–4 |
| MM-REQ-031 | Mission 不得接收或构造 MoveIt `RobotTrajectory`，planner/controller细节必须封装在 Manipulation Adapter。 | package dependency/static test | 3–4 |
| MM-REQ-032 | Manipulation result 必须分别记录 planning outcome、trajectory dispatch、controller execution outcome 与 quality outcome。 | adapter result test | 3–5 |
| MM-REQ-033 | Planning failure 必须映射 `PLANNING_FAILED`；controller/trajectory failure 必须映射 `EXECUTION_FAILED`，不得合并成 bool false。 | injected failure tests | 3/7 |
| MM-REQ-034 | `scan` 必须使用 station/workpiece-relative raster/line recipe、受控 TCP orientation、velocity limits 与 collision checking。 | plan inspection + runtime trace | 5 |
| MM-REQ-035 | Cartesian path 低于 versioned minimum fraction时不得执行；partial path 不得标记 scan success。 | unit + MoveIt integration test | 5 |
| MM-REQ-036 | `pick` 必须显式包含 approach、gripper close、grasp confirmation、retreat；arm trajectory success 不等于 grasp success。 | Gate 6 runtime evidence | 6 |
| MM-REQ-037 | `place` 必须显式包含 approach、release、release confirmation 与 retreat；release unknown不得进入 final success。 | Gate 6 runtime evidence | 6 |
| MM-REQ-038 | `stow` 只有 measured joints/velocity/stable-duration通过 named-state gate 后才返回 STOWED。 | controller-state quality test | 3–4 |
| MM-REQ-039 | Manipulation Adapter 同时最多拥有一个 active command，并拒绝不匹配 command identity 的 cancel/result。 | concurrency/late-result tests | 4 |
| MM-REQ-040 | MoveIt planning scene 必须包含 mobile base、arm、gripper、workcell collision geometry 与当前 workpiece/attached object状态。 | planning-scene inspection | 3/6 |
| MM-REQ-041 | 当 BaseState 不是 fresh `STATIONARY` 时，Manipulation Adapter 必须拒绝 admission，不得发送 MoveIt/controller goal。 | interlock fault test | 4/7 |

## 6. Perception 与 TF

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-050 | Stage A/B/C 必须输出同一 `WorkpiecePose` contract，Mission 不得根据 provider 类型改变 FSM。 | provider contract tests | 4–5 |
| MM-REQ-051 | `WorkpiecePose` 至少包含 object/observation identity、frame、position/orientation、capture timestamp、received timestamp、quality/confidence、source及source version。 | schema test | 4 |
| MM-REQ-052 | Perception Adapter 必须拒绝 zero/future/invalid timestamp、wrong object、wrong frame/provenance与超过 maximum age 的 pose。 | timestamp/provenance tests | 4/7 |
| MM-REQ-053 | Manipulation Adapter 必须在 dispatch 前再次校验 pose freshness；scan 后 pose 超龄必须重新 perception。 | clock-controlled integration test | 5–6 |
| MM-REQ-054 | Target transform 必须在 observation timestamp 查询；transform unavailable或extrapolation失败时不得使用 latest pose兜底。 | TF buffer tests | 4–5 |
| MM-REQ-055 | Stage A 必须从 Gazebo authoritative object pose生成 contract，并记录 `source=GAZEBO_GROUND_TRUTH`；该标签不得提升为视觉验证。 | Stage A provider runtime test | 4–5 |
| MM-REQ-056 | Stage B fiducial 必须通过 camera image/detection/extrinsic/TF生成同一 contract，并记录 detector/calibration version。 | Stage B optional runtime test | 5 |
| MM-REQ-057 | Stage C RGB-D/detector/point-cloud不得成为 V1 completion依赖。 | scope/dependency audit | 0–7 |
| MM-REQ-058 | `map -> odom`、`odom -> base_link`、robot kinematic chain、camera、station和workpiece TF edge必须各有唯一 authority。 | TF graph/duplicate-authority test | 1–5 |
| MM-REQ-059 | Scan/pick/place recipes 应以 `station_*_frame` 或 `workpiece_frame` 表达，不得只保存无来源的 map/world hard-coded pose。 | config/schema review | 5–6 |
| MM-REQ-060 | Gazebo world 与 Nav2 map 的 alignment 必须有 versioned transform/config与 runtime validation，不得因坐标数字相近而假定同 frame。 | alignment report | 1–2 |

## 7. Robot State 与 Interlock

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-070 | 系统必须显式提供 `BaseState = MOVING/STATIONARY/FAULT/UNKNOWN` 与 `ArmState = STOWED/ACTIVE/FAULT/UNKNOWN`。 | state contract test | 4 |
| MM-REQ-071 | 系统必须强制 `Base MOVING => Arm STOWED` 与 `Arm ACTIVE => Base STATIONARY`。 | interlock truth-table + runtime tests | 4/7 |
| MM-REQ-072 | state sample超过 freshness deadline或source unavailable时必须变为 UNKNOWN并拒绝新 motion。 | clock/source-loss test | 4/7 |
| MM-REQ-073 | Interlock admission必须绑定 task/execution/command/state revision与expiry，旧 permit不得启动动作。 | permit/revision tests | 4 |
| MM-REQ-074 | invariant在执行中被破坏时必须 revoke permit并触发对应 adapter stop/cancel，记录 typed fault。 | runtime fault injection | 7 |
| MM-REQ-075 | process shutdown必须先阻止新 admission，再 cancel/stop active command并有界等待；无法确认时记录 outcome unknown/stop unconfirmed。 | SIGTERM/shutdown test | 7 |
| MM-REQ-076 | 软件 Interlock 文档与输出不得宣称 E-stop、protective stop、functional safety或认证 safety layer。 | claim audit | 0–7 |

## 8. Arrival / Execution Quality

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-080 | Base stationary gate必须使用 fresh odometry/twist、linear/angular speed与stable duration，不能只用 Nav2 result或sleep。 | synthetic + Gazebo trace test | 4 |
| MM-REQ-081 | Ready-for-scan/pick gate必须评估 target freshness、TF-at-stamp、position/orientation error、joint velocity、TCP velocity与stable duration。 | quality-gate tests | 4–5 |
| MM-REQ-082 | MoveIt/controller `SUCCESS` 不得单独产生 `READY_FOR_PICK` 或 Mission phase success。 | transition guard test | 5–6 |
| MM-REQ-083 | 所有 threshold必须来自 versioned config，并在无现实依据时标记 `DEMO THRESHOLD`。 | config/report audit | 4–6 |
| MM-REQ-084 | Gate 4/5 acceptance report必须记录 threshold来源、采样频率、观测分布与残余风险，不得称工业标准。 | report review | 4–5 |

## 9. Fault、Cancel、Retry 与旧动作隔离

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-090 | Fault contract至少区分 `NAVIGATION_FAILED/PERCEPTION_STALE/TARGET_UNREACHABLE/PLANNING_FAILED/EXECUTION_FAILED/GRASP_FAILED/ARM_NOT_STOWED/BASE_NOT_STATIONARY/CANCELED/TIMEOUT/ARM_FAULT`。 | enum/schema test | 4 |
| MM-REQ-091 | Fault必须包含 phase、source、retry disposition、certainty、command identity与human-readable detail，不能只返回 bool。 | schema test | 4 |
| MM-REQ-092 | 自动 retry必须有 versioned policy、attempt上限与deadline；每次 retry必须产生新 attempt/command identity。 | retry tests | 4–7 |
| MM-REQ-093 | 只有确认无物理副作用或可安全重复的 failure才允许自动 retry；grasp unknown、arm fault、execution failure、stop unconfirmed、place ambiguity与cancel不得自动 retry。 | policy table tests | 4–7 |
| MM-REQ-094 | stale workpiece pose必须阻止 scan/pick，Mission不得错误进入 PICKING。 | mandatory fault case 1 | 7 |
| MM-REQ-095 | trajectory execution failure必须阻止下一 phase并记录 `EXECUTION_FAILED`，不得写 success。 | mandatory fault case 3 | 7 |
| MM-REQ-096 | 所有 feedback/result/cancel response必须按 execution/command identity与expected phase过滤；旧 result只能审计记录，不能推进当前 FSM。 | delayed callback/race test | 4/7 |
| MM-REQ-097 | Task进入 FAILED/CANCELED前必须确认 active child command terminal且robot quiescent；否则进入 `RECOVERY/OUTCOME_UNKNOWN`。 | stop-confirmation tests | 7 |

## 10. Evidence、可追踪性与 Upstream

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| MM-REQ-100 | 每个 Mission transition与child command terminal fact必须持久化，至少带task/execution/attempt/command ID、timestamp、state revision、source与result/fault。 | event schema + replay test | 4–7 |
| MM-REQ-101 | 大体积artifact必须以reference + hash保存；不得只把mutable path或图片blob塞进task status。 | artifact/evidence test | 5–7 |
| MM-REQ-102 | local execution fact必须先于WMS/Dashboard projection持久化；projection retry必须idempotent。 | outage/retry test | 6–7 |
| MM-REQ-103 | 每份 Gate report必须记录 branch/HEAD、dirty state、dependency versions、commands、result、evidence label与not-tested boundary。 | report checklist | 0–7 |
| MM-REQ-104 | Upstream必须记录 repo URL、pin、ROS/Gazebo/MoveIt/control versions、baseline launch、dependencies与known assumptions。 | provenance manifest review | 0–1 |
| MM-REQ-105 | 必须先在隔离 workspace复现选定upstream baseline，再记录requirement delta和adapter/patch决策；未复现不得进入composite integration。 | upstream reproduction report | 0–1 |
| MM-REQ-106 | 只有存在明确requirement gap且adapter无法满足时才patch upstream core；patch必须最小、可追溯且有回归。 | ADR/diff/test review | 1–7 |

## 11. V1 completion rule

V1 只有在 Gate 0–7 的 mandatory requirements全部有对应证据、三项mandatory fault cases通过且没有 unresolved stop/ownership/TF conflict时才可以称为：

```text
Gazebo Harmonic Mobile Manipulation V1 vertical slice VERIFIED
```

它仍然不得称为真实硬件、工业抓取、functional safety或Sim2Real verified。
