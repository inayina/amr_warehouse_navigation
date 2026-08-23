# Heterogeneous Fleet System Context

日期：`2026-08-23`
状态：Requirements Context Only

本文件只描述 actors、边界和职责；需求与验收标准见 [HETEROGENEOUS_FLEET_REQUIREMENTS.md](./HETEROGENEOUS_FLEET_REQUIREMENTS.md)。

## 1. Actors

| Actor | Interaction with the system |
| --- | --- |
| Operations operator | 查看机器人、任务、不可派发原因和故障投影；不直接拥有控制状态。 |
| Fleet administrator | 批准部署 profile、capability policy 和机器人启用范围。 |
| Robot integration engineer | 接入 vendor SDK/transport，提供 adapter contract 与 evidence provenance。 |
| Maintenance engineer | 诊断 Robot、Device、Runtime、adapter、网络和 vendor 故障。 |
| Task/WMS system | 提交 vendor-neutral task requirements，消费任务状态/writeback。 |
| Local robot runtime | 维护 execution-side operational state、watchdog、navigation/control 和 safety gate。 |
| Vendor SDK / robot | 提供 vendor-specific telemetry/control contract。 |
| Go robot-platform-service | 聚合 inventory、management liveness、history 和 API-facing projection。 |

## 2. System boundary

```text
                         Operators / Administrators
                                    |
                                    v
                  +----------------------------------+
                  |       MANAGEMENT PLANE           |
                  | robot-platform-service (future)  |
                  | inventory / Runtime liveness /   |
                  | profile projection / Run history |
                  +----------------+-----------------+
                                   ^ asynchronous projection/sync
                                   | NOT IN CONTROL LOOP
                                   v
Task / WMS --------------> +-------------------------------+
                           |          FLEET DOMAIN          |
                           | RobotRegistry / Dispatcher /   |
                           | task lifecycle / resource lock |
                           +-------------+-----------------+
                                         |
                                         v
                           +-------------------------------+
                           |        EXECUTION PLANE        |
                           | RobotExecutionContext         |
                           | AMR/Nav2: implemented         |
                           | third-party vendors:          |
                           | NOT IMPLEMENTED               |
                           +-------------+-----------------+
                                         |
                                         v
                           Local controllers / safety loops

Vendor robot/SDK --> adapter --> normalized state/liveness --> RobotRegistry
       STATE PLANE; vendor schema stops at adapter boundary
```

Current cross-repository reality: `amr_warehouse_navigation` and `robot-platform-service` are **not integrated**. The arrow to Management Plane is a requirement boundary, not an implemented data path.

## 3. State Plane

```text
Robot/vendor telemetry
-> ROS 2 / DDS / TCP SDK / process IPC
-> vendor adapter
-> normalized observation
-> RobotRegistry operational state input
```

Responsibilities:

- adapter owns vendor type/topic/ABI/process lifecycle and validation;
- RobotRegistry owns local business/operational state transitions;
- telemetry can establish liveness only within its stated evidence boundary;
- Platform may receive a lower-rate projection, but cannot overwrite local execution authority;
- vendor-specific schema never enters Dispatcher.

## 4. Execution Plane

```text
Task requirement
-> eligible robot selection
-> assignment / resource ownership
-> RobotExecutionContext
-> vendor-specific execution implementation
-> local controller / robot
```

Current evidence:

| Boundary | Status |
| --- | --- |
| AMR / Nav2 execution | Existing project baseline |
| Vendor-neutral execution seam | Implemented and unit-tested with fake context |
| DR02 / Unitree / Agibot Fleet execution | NOT IMPLEMENTED |
| Heterogeneous concurrent task execution | NOT TESTED |

Execution Plane owns current task transition, ready gate, timeout/cancel/result, local watchdog and safety behavior. No Platform call belongs on this synchronous path.

## 5. Management Plane

Future Go Platform integration is limited to:

- canonical Robot/Device/Runtime identity and inventory;
- RuntimeSession and management heartbeat/liveness history;
- approved Robot Profile/capability metadata projection;
- Run/task correlation and diagnostic/evidence references;
- API/dashboard-facing aggregation.

It does not own:

- real-time navigation, joint/motor control or locomotion;
- watchdog, E-stop, controller deadline or local safe stop;
- Fleet assignment/current task authority;
- vendor command semantics;
- automatic capability evidence promotion;
- domain artifact contents.

## 6. External systems

| External system | Contract boundary |
| --- | --- |
| WMS / task source | Submits task envelope and receives writeback; does not select vendor. |
| Vendor SDK / robot | Provides vendor-specific state/control; isolated behind adapter/execution implementation. |
| Robot/edge device | Hosts local Runtime and safety loops; continues safely when Platform is unavailable. |
| Evidence store/artifacts | Domain-owned evidence remains external; Platform uses typed references. |
| Dashboard/API consumer | Reads management projections and timestamps; does not become execution authority. |

## 7. Responsibility matrix

Legend: `A` authoritative, `P` projection/reference, `I` integration owner, `—` no ownership.

| Responsibility | Fleet / RobotRegistry | Execution Runtime | Vendor adapter | Fleet admin / validation | Go Platform | WMS | Vendor SDK |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Robot operational business state | A | input | input | policy | P | P | — |
| Current task / assignment | A | executes | — | policy | P | external task authority/writeback peer | — |
| Local execution readiness | A decision input | A | input | policy | — | — | input |
| Vendor telemetry normalization | — | — | A/I | reviews | P | — | source |
| Local liveness for eligibility | A | input | input | defines threshold | P | — | source |
| Management Runtime liveness | P | producer | producer | consumes | A | — | — |
| Capability claim provenance | consumes approved profile | evidence producer | I | A for approval record | P/index | requirement consumer | declared source |
| Capability maturity promotion | policy consumer | evidence input | evidence input | A after validation | P/index only | — | cannot promote project evidence |
| Task requirement | consumes | — | — | defines policy bounds | P | A/source | — |
| Resource ownership | A | obeys | — | policy | P | — | — |
| Watchdog / E-stop / safe stop | — | A | vendor-local contribution | cannot override | — | — | vendor-local contribution |
| Run history/correlation | source | authoritative execution result | diagnostic source | reviews | A for envelope/projection | P | — |

`A` is intentionally split by fact type: local Fleet owns execution truth; Platform owns management history/projection. The same field must not have two writers.

## 8. Failure boundary summary

```text
Platform/network failure
    -> management data stale/gapped
    -> local execution and safety continue

Vendor telemetry/adapter failure
    -> local robot loses eligibility
    -> task follows reversible/irreversible boundary
    -> Platform receives a projection when available

Fleet failure
    -> Platform keeps last projection only
    -> projection becomes stale/offline/unknown
    -> Platform does not infer task completion
```

This context does not assign fixed roles to DEEPRobotics, Unitree or Agibot and does not claim a production heterogeneous Fleet.
