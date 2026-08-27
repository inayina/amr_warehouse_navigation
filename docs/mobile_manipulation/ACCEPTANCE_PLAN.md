# Mobile Manipulation V1 Acceptance Plan

日期：`2026-08-27`

状态：**ACCEPTANCE DESIGN / MOBILE MANIPULATION RUNTIME NOT IMPLEMENTED**

## 1. 验收结论边界

本计划回答“每条 `MM-REQ` 由什么事实证明”。它不把文档完成、源码存在、单元测试、MoveIt planning、Gazebo motion、simulation grasp 或完整业务任务混为同一种证据。

V1 的最高可用结论是：

```text
Gazebo Harmonic Mobile Manipulation V1 vertical slice VERIFIED
```

该结论只有在 Gate 0–7 的 mandatory criteria、三项 mandatory fault case、完整任务 success predicate 和 evidence manifest 全部通过后才允许使用。它仍不代表真机、工业抓取、Sim2Real、功能安全或认证性能。

## 2. 证据层级与允许声明

| Level | 必要事实 | 允许声明 | 不允许外推 |
| --- | --- | --- | --- |
| D0 — Document/static | schema、launch/config、依赖和 ownership 可审计 | `SOURCE-AUDITED` | runtime 可启动或行为正确 |
| D1 — Unit/mock | clock-controlled unit、fake Action、pure FSM、deterministic mock | `MOCK-VERIFIED`，注明 mock 范围 | Gazebo、Nav2、MoveIt/controller 成功 |
| D2 — Component runtime | 单组件在 ROS/Gazebo 中启动并产生 expected state/result | scoped `VERIFIED`，如 controller bringup | manipulation task success |
| D3 — Integration runtime | 两个或多个真实 runtime boundary 完成交接 | scoped integration `VERIFIED` | grasp、place或end-to-end success，除非分别证明 |
| D4 — Scenario runtime | 同一 execution 完成完整 V1 success predicate并持久化证据 | Gazebo V1 vertical slice `VERIFIED` | physical/industrial/Sim2Real success |
| D5 — Fault/runtime | 注入失败、cancel、shutdown和late result并证明fail-closed | scoped resilience `VERIFIED` | functional safety certification |

统一标签：

- `VERIFIED`：必须附 checkout、环境、命令、时间、result和artifact reference；只覆盖实际执行范围。
- `SOURCE-AUDITED`：只表示读过当前源码/config或官方 upstream。
- `MOCK-VERIFIED`：只表示fake/mock/deterministic simulated context通过。
- `NOT TESTED`：没有当轮运行证据，或仍是design/assumption/候选threshold。

以下关系必须始终保持：

```text
pytest PASS
  != Gazebo launch PASS
  != Nav2 task PASS
  != MoveIt plan PASS
  != trajectory execution PASS
  != grasp/release confirmation
  != WorkcellTask SUCCESS
```

## 3. Gate acceptance matrix

| Gate | Acceptance ID | 必须运行的主要证明 | Exit claim | 当前状态 |
| --- | --- | --- | --- | --- |
| 0 | `MM-ACC-G0` | existing pytest regression；fresh current Nav2 smoke；U1/U2/U3 upstream standalone reproduction；dependency freeze | AMR baseline仍成立、upstream route可复现 | pytest `VERIFIED`；live/upstream `NOT TESTED` |
| 1 | `MM-ACC-G1` | combined description、TF uniqueness、controller/resource claims、arm/gripper command、base contract、physics sanity | Gazebo controller bringup `VERIFIED` | `NOT TESTED` |
| 2 | `MM-ACC-G2` | MM variant localization/Nav2；short/A/B goals；stationary trace；stowed envelope/footprint；map/world alignment | MM base Nav2 baseline `VERIFIED` | `NOT TESTED` |
| 3 | `MM-ACC-G3` | MoveIt current state；joint/pose plan and execute；collision rejection；measured stow quality | stationary arm planning/execution baseline `VERIFIED` | `NOT TESTED` |
| 4 | `MM-ACC-G4` | typed adapters；FSM handoff；Base/Arm observers；permit/revoke；identity fencing；cancel happy path | Nav2→stationary→MoveIt handoff `VERIFIED` | `NOT TESTED` |
| 5 | `MM-ACC-G5` | Stage A WorkpiecePose；TF-at-stamp；stale rejection；raster fraction/collision/quality；artifacts | perception→scan vertical slice `VERIFIED` | `NOT TESTED` |
| 6 | `MM-ACC-G6` | pick/grasp/stow/transport/place/release/final stow；attached object consistency；durable success evidence | deterministic Gazebo task vertical slice `VERIFIED` | `NOT TESTED` |
| 7 | `MM-ACC-G7` | mandatory faults；cancel/timeout/shutdown/restart/late result；quiescence or quarantine | scoped fault/cancel resilience `VERIFIED` | `NOT TESTED` |

后续 Gate 不得补写前一 Gate 的缺失证据。若 dependency、model或stable baseline发生变化，受影响 Gate 必须重新验证。

## 4. Requirement traceability

### 4.1 Baseline 与 task contract

| Requirement | Planned proof | 最低层级 | Gate |
| --- | --- | --- | --- |
| `MM-REQ-001` | protected-file hashes；default launch graph before/after；opt-in launch test | D0+D2 | 0–1 |
| `MM-REQ-002` | exact command的full pytest/colcon report，保留原始失败 | D1 | 0–7 |
| `MM-REQ-003` | config/runtime graph仅一个robot、一个arm、一个active task | D0+D3 | 1–7 |
| `MM-REQ-004` | environment/package/process inventory无Isaac/MuJoCo runtime | D0+D2 | 0–7 |
| `MM-REQ-005` | upstream lock/provenance manifest；dependency/include/adapter diff review | D0 | 0–1 |
| `MM-REQ-006` | README、report和artifact claim lint/manual review | D0 | 0–7 |
| `MM-REQ-010` | WorkcellTask schema serialization/invalid-field tests | D1 | 0/4 |
| `MM-REQ-011` | repeated execution/attempt产生unique IDs；callback correlation test | D1+D3 | 4 |
| `MM-REQ-012` | transition-table exhaustive test；non-owner write rejection | D1 | 4 |
| `MM-REQ-013` | independent business/mission/action/robot state schemas和transition assertions | D0+D1 | 4 |
| `MM-REQ-014` | expired/future/missing/unsupported task matrix；assert zero motion command | D1+D3 | 4 |
| `MM-REQ-015` | simultaneous claim/admission race；exactly one winner，loser fail closed | D1+D3 | 4 |
| `MM-REQ-016` | end-to-end success predicate逐项assert，含evidence persisted和no active command | D4 | 6 |
| `MM-REQ-017` | package dependency/layer import test；Mission call trace只到adapters | D0+D1 | 4 |
| `MM-REQ-018` | simulated clock和nested commands证明absolute deadline不重置 | D1 | 4 |

### 4.2 Navigation 与 manipulation

| Requirement | Planned proof | 最低层级 | Gate |
| --- | --- | --- | --- |
| `MM-REQ-020` | dependency/static boundary test；Mission无Nav2 plugin或`/cmd_vel` dependency | D0+D1 | 4 |
| `MM-REQ-021` | station→NavigateToPose mapping、goal identity和Nav2 status trace | D3 | 2–4 |
| `MM-REQ-022` | SUCCEEDED/ABORTED/CANCELED/timeout result mapping matrix | D1+D3 | 4/7 |
| `MM-REQ-023` | lifecycle、TF、Action、fresh state和permit逐项失效注入 | D3+D5 | 2–4/7 |
| `MM-REQ-024` | mandatory fault Case 2；assert no Nav2 goal and no base motion | D5 | 4/7 |
| `MM-REQ-025` | Nav2 success后FSM只到`WAIT_BASE_STATIONARY_*`的transition trace | D1+D3 | 4 |
| `MM-REQ-026` | cancel request→accepted/rejected→terminal Action state→physical stop trace | D5 | 4/7 |
| `MM-REQ-027` | timeout、cancel-ack timeout、stop-unconfirmed injection；ownership remains held | D5 | 7 |
| `MM-REQ-028` | Station A/B repeated pose、reach、camera、collision、footprint report | D3 | 2–3 |
| `MM-REQ-029` | ROS graph publisher inventory + source dependency test | D0+D3 | 2–7 |
| `MM-REQ-030` | Mission dependency test只出现scan/pick/place/stow/stop/state contract | D0+D1 | 3–4 |
| `MM-REQ-031` | Mission package无MoveIt trajectory dependency；runtime call trace到adapter | D0+D1 | 3–4 |
| `MM-REQ-032` | plan/dispatch/controller/quality分别持久化和组合结果test | D1+D3 | 3–5 |
| `MM-REQ-033` | planning failure和controller failure分别注入并检查typed fault | D1+D5 | 3/7 |
| `MM-REQ-034` | raster/line recipe trace；TCP orientation、limits、collision settings检查 | D3 | 5 |
| `MM-REQ-035` | below-threshold Cartesian fraction injection；assert no execution goal | D1+D3 | 5 |
| `MM-REQ-036` | approach/close/confirmation/retreat phase trace与独立grasp fact | D4 | 6 |
| `MM-REQ-037` | approach/release/confirmation/retreat trace；unknown release prevents success | D4+D5 | 6–7 |
| `MM-REQ-038` | measured joint error/velocity/stable-window boundary tests | D1+D3 | 3–4 |
| `MM-REQ-039` | concurrent commands、wrong cancel、delayed result fencing | D1+D5 | 4/7 |
| `MM-REQ-040` | planning scene snapshot；base/arm/gripper/workcell/object collision checks | D3 | 3/6 |
| `MM-REQ-041` | moving/stale/unknown BaseState injection；assert no controller goal | D5 | 4/7 |

### 4.3 Perception、TF、Interlock 与 quality

| Requirement | Planned proof | 最低层级 | Gate |
| --- | --- | --- | --- |
| `MM-REQ-050` | Stage A/B provider contract conformance suite；Mission fixture不变 | D1+D3 | 4–5 |
| `MM-REQ-051` | WorkpiecePose schema round-trip和required-field validation | D1 | 4 |
| `MM-REQ-052` | zero/future/stale/wrong-object/frame/source/version table tests | D1+D5 | 4/7 |
| `MM-REQ-053` | fresh at observation but stale at dispatch的controlled-clock test | D1+D3 | 5–6 |
| `MM-REQ-054` | exact-stamp TF success/failure/extrapolation test；assert no latest fallback | D1+D3 | 4–5 |
| `MM-REQ-055` | Gazebo entity pose→contract runtime trace，source严格为GT | D3 | 4–5 |
| `MM-REQ-056` | optional real image→fiducial detection→TF→same contract trace | D3 | 5 optional |
| `MM-REQ-057` | dependency/process inventory确认V1 completion不依赖Stage C | D0+D2 | 0–7 |
| `MM-REQ-058` | `view_frames`/topic authority inventory；duplicate-edge negative launch test | D2+D3 | 1–5 |
| `MM-REQ-059` | recipe config使用station/workpiece frame；world-number lint/review | D0+D3 | 5–6 |
| `MM-REQ-060` | versioned world↔map alignment config、landmark comparison和runtime report | D3 | 1–2 |
| `MM-REQ-070` | BaseState/ArmState contract truth table和UNKNOWN paths | D1 | 4 |
| `MM-REQ-071` | all invariant combinations + runtime opposing-domain admission tests | D1+D5 | 4/7 |
| `MM-REQ-072` | odom/joint-state source loss和age boundary tests | D1+D5 | 4/7 |
| `MM-REQ-073` | expired/wrong identity/wrong revision permit rejection | D1 | 4 |
| `MM-REQ-074` | execution中invariant break；permit revoked、stop invoked、fault persisted | D5 | 7 |
| `MM-REQ-075` | SIGTERM in each active domain；bounded wait与unknown/quarantine result | D5 | 7 |
| `MM-REQ-076` | code/docs/report safety-claim review | D0 | 0–7 |
| `MM-REQ-080` | synthetic odom thresholds + Gazebo velocity/stable-duration trace | D1+D3 | 4 |
| `MM-REQ-081` | target/TF/pose error/joint/TCP velocity/stability guard boundary matrix | D1+D3 | 4–5 |
| `MM-REQ-082` | planner/controller success但quality fail；assert FSM不进入ready/next phase | D1+D3 | 5–6 |
| `MM-REQ-083` | threshold config schema/version/hash与`DEMO THRESHOLD` report lint | D0+D1 | 4–6 |
| `MM-REQ-084` | Gate report包含来源、采样率、分布、残余风险 | D0+D3 | 4–5 |

### 4.4 Fault、evidence 与 upstream

| Requirement | Planned proof | 最低层级 | Gate |
| --- | --- | --- | --- |
| `MM-REQ-090` | FaultCode enum/schema exhaustiveness test | D1 | 4 |
| `MM-REQ-091` | required fault fields、certainty和identity round-trip test | D1 | 4 |
| `MM-REQ-092` | retry attempt limit/deadline/new identity property tests | D1+D5 | 4–7 |
| `MM-REQ-093` | policy table覆盖safe/forbidden retry；runtime forbidden-case assertions | D1+D5 | 4–7 |
| `MM-REQ-094` | mandatory fault Case 1 | D5 | 7 |
| `MM-REQ-095` | mandatory fault Case 3 | D5 | 7 |
| `MM-REQ-096` | delayed feedback/result/cancel after new execution；state unchanged、audit retained | D1+D5 | 4/7 |
| `MM-REQ-097` | failure/cancel with active child；terminal+quiescent or recovery/unknown | D5 | 7 |
| `MM-REQ-100` | event schema、ordered transition log和replay/reconciliation test | D1+D4 | 4–7 |
| `MM-REQ-101` | artifact hash verification；mutable/missing artifact negative tests | D1+D4 | 5–7 |
| `MM-REQ-102` | WMS unavailable/recovery；local fact first、idempotent projection | D1+D5 | 6–7 |
| `MM-REQ-103` | automated report schema/checklist validation | D0+D1 | 0–7 |
| `MM-REQ-104` | official URL/tag/commit/version/baseline/assumption manifest review | D0 | 0–1 |
| `MM-REQ-105` | isolated-workspace reproduction logs and requirement-delta report | D2 | 0–1 |
| `MM-REQ-106` | ADR证明adapter不足；minimal patch provenance/diff/regression | D0+D1 | 1–7 |

## 5. Mandatory fault cases

### Case 1 — stale WorkpiecePose

**Precondition:** robot stationary，arm可用，pose的source/provenance合法但`now - capture_stamp > max_age`，或在dispatch前超龄。

**Stimulus:** Mission请求scan或pick。

**必须观察：**

- Perception/Manipulation admission拒绝；
- zero MoveIt/controller goal；
- Mission不得进入`SCANNING`或`PICKING`，而进入bounded re-perception或typed failure；
- fault为`PERCEPTION_STALE`，包含pose identity、timestamps、threshold version；
- task不得写`SUCCESS`。

### Case 2 — arm not STOWED while navigation requested

**Precondition:** ArmState为fresh `ACTIVE`，或`FAULT/UNKNOWN/stale`。

**Stimulus:** Mission或测试client请求navigate。

**必须观察：**

- Interlock不签发Navigation permit，Navigation Adapter admission rejected；
- zero Nav2 goal，base measured velocity保持stationary；
- fault为`ARM_NOT_STOWED`或state-unavailable typed fault；
- 不通过自动发送stow掩盖本次非法请求；recovery必须是显式新command。

### Case 3 — trajectory execution failed

**Precondition:** planning success且controller接受trajectory。

**Stimulus:** controller abort、path tolerance violation或明确execution fault。

**必须观察：**

- result为`EXECUTION_FAILED`，与planning结果分离；
- FSM不进入下一业务phase，不启动grasp/base navigation；
- active command先terminal且robot state确认；若无法确认则Mission进入`RECOVERY/OUTCOME_UNKNOWN`，不得进入terminal task state；
- 无自动retry，除非未来policy对一个明确safe、无副作用case另有版本化批准；
- WMS/task不得写`SUCCESS`。

每个Case必须同时保存positive control，证明相同fixture在不注入fault时可到达目标前置状态，避免“系统根本没启动”造成伪通过。

## 6. Additional Gate 7 matrix

| Injection | Expected fail-closed behavior | Required artifact |
| --- | --- | --- |
| Nav2 abort | `NAVIGATION_FAILED`；no manipulation；terminal + stationary | Nav2 result、odom stop trace、FSM events |
| MoveIt planning failure | `PLANNING_FAILED`；zero controller dispatch | plan result、controller goal inventory |
| cancel during navigation | cancel传播、terminal Action、base stop；否则quarantine | request/ack/result/odom timeline |
| cancel during manipulation | stop/cancel传播；不得推进phase | controller result、joint/TCP stop trace |
| cancel after grasp | no auto requeue；held-object uncertainty进入recovery | grasp/attachment/state snapshot |
| grasp or release unknown | no transport/success；manual/recovery disposition | confirmation-source record |
| action/cancel timeout | ownership不释放；`TIMEOUT`/stop-unconfirmed | deadline、ack和state trace |
| odom/joint source stale | state→UNKNOWN；new motion denied | sample-age timeline |
| TF unavailable/extrapolation | target rejected；no latest fallback | lookup stamp/error、goal inventory |
| Evidence Store failure | local task success不得提交；projection不得伪成功 | store error、event state |
| SIGTERM | admission closed；bounded stop；known or unknown outcome persisted | shutdown timeline/process exit |
| late success after cancel | retained for audit only；current FSM unchanged | old/new command IDs、state revision |
| restart with active execution | reconcile or quarantine；不得blind resend | pre/post restart event log |

## 7. End-to-end V1 success predicate

同一 `task_id/execution_id` 必须按顺序有可关联事实：

1. task valid且single-owner claim成立；
2. Station A Nav2 Action `SUCCESS`；
3. fresh measured BaseState持续`STATIONARY`；
4. fresh、正确object/frame/source的WorkpiecePose与TF-at-stamp有效；
5. scan plan、dispatch、controller execution和quality gate分别通过；
6. fresh pick target有效；pick execution与grasp confirmation分别通过；
7. measured ArmState持续`STOWED`且held-object state一致；
8. Station B Nav2 Action `SUCCESS`和fresh stationary gate通过；
9. place execution、release confirmation和acceptance region分别通过；
10. final measured ArmState为`STOWED`；
11. 所有child command terminal，无unresolved cancel/stop/attachment/ownership；
12. transition log、artifact references/hashes和result summary先durably persisted；
13. WMS projection最后以idempotent update写`SUCCESS`。

任一事实未知、stale或缺失时不得靠后续事实补成success。

## 8. Runtime protocol

每个runtime acceptance至少执行：

1. clean process/device inventory与dependency snapshot；
2. build/test，记录完整命令和exit code；
3. launch后等待explicit ready gate，不用固定sleep代替readiness；
4. 执行positive control；
5. 执行目标scenario/fault injection；
6. 保存ROS Action/result、TF/controller/resource、odom/joint/quality和event artifacts；
7. 有界shutdown并确认无orphan goal/controller/process；
8. 对artifact计算hash并生成manifest；
9. 恢复control group，复跑existing baseline regression；
10. 写result、limitations和`NOT TESTED`边界。

repeatability run count和成功率阈值在Gate 0/2依据仿真稳定性正式冻结；在此之前统一标记`DEMO THRESHOLD / NOT TESTED`，不先写一个看似工业化的百分比。

## 9. Evidence bundle

每次Gate运行建议保存：

```text
evidence/mobile_manipulation/<gate>/<run_id>/
├── manifest.json
├── environment.json
├── commands.jsonl
├── ros_graph.json
├── events.jsonl
├── actions.jsonl
├── tf_authority.json
├── controller_resources.json
├── state_trace.csv
├── quality_summary.json
├── artifacts/
└── report.md
```

`manifest.json` 至少包含：branch、full HEAD、dirty state、ROS/Gazebo/dependency versions、scenario/config/threshold/calibration versions、task/execution IDs、start/end ROS与host time、commands、exit codes、artifact references、SHA-256、evidence label和not-tested list。未同步clock之间的latency不得伪造；无法比较时记录`UNAVAILABLE`。

## 10. Gate report decision template

```text
Gate:
Checkout / dirty state:
Environment and dependency lock:
Requirement IDs exercised:
Commands:
Observed results:
Artifact manifest and hashes:
Evidence label and exact scope:
Failures / unknowns / NOT TESTED:
Stable baseline regression:
Decision: PASS | FAIL | BLOCKED
Authorized next Gate:
```

只有`Decision: PASS`且没有当前Gate hard stop，才允许请求进入下一Gate；`BLOCKED`不是`PASS with caveats`。
