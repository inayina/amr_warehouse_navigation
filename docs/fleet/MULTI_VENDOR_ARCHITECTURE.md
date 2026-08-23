# Multi-Vendor Robot Integration Architecture

日期：`2026-08-23`

## 1. Scope

当前只验证三家 vendor 向内部 Fleet `RobotRegistry` 提供**状态/存活（state/liveness）**信息的窄集成边界。

它不是 heterogeneous task execution、生产 Fleet 或真机部署。没有 capability schema、vendor-aware dispatch、vendor navigation context 或 Fleet command implementation。

本文件只使用以下证据标签：

| Label | Meaning |
| --- | --- |
| `VERIFIED` | 有实际运行证据，且记录了运行边界。 |
| `SOURCE-AUDITED` | 官方源码或文档已核对，但本机没有对应 runtime。 |
| `MOCK-VERIFIED` | fake message/process/IPC contract 已运行；不是 vendor runtime。 |
| `NOT TESTED` | 没有相关证据。 |

## 2. Current system boundary

```text
                         Fleet / Ops
                             |
                       RobotRegistry
                             |
                internal liveness only
                             |
       +---------------------+---------------------+
       |                     |                     |
 DeepRobotics adapter   Unitree adapter      Agibot adapter
       |                     |                     |
 ROS 2 callback          ROS 2 callback       JSONL IPC
 [VERIFIED]              [MOCK-VERIFIED]      [MOCK-VERIFIED]
       |                     |                     |
 DR02 Pro MuJoCo         Go2 MuJoCo            D1 MaxPro C++ probe
 /JOINTS_DATA            /lowstate             createQuadruped/init/
 [VERIFIED]              [SOURCE-AUDITED]      GetRobotStatus
                                                 [SOURCE-AUDITED]
```

`RobotRegistry` does not import a vendor SDK. Every adapter is opt-in, validates only its own transport boundary, and calls `record_heartbeat(..., recover_offline=False)`. Telemetry arrival is therefore not an `IDLE` transition, task completion, battery update, pose update, or execution-capability claim.

## 3. Evidence matrix

| Link | DEEPRobotics DR02 Pro | Unitree Go2 | Agibot D1 MaxPro |
| --- | --- | --- | --- |
| Official SDK audited | SOURCE-AUDITED | SOURCE-AUDITED | SOURCE-AUDITED |
| Telemetry source identified | VERIFIED (`/JOINTS_DATA`) | SOURCE-AUDITED (`/lowstate` / `rt/lowstate`) | SOURCE-AUDITED (`GetRobotStatus`) |
| Vendor runtime | VERIFIED (MuJoCo telemetry) | SOURCE-AUDITED | NOT TESTED |
| Adapter runtime | VERIFIED | MOCK-VERIFIED | MOCK-VERIFIED |
| Internal heartbeat / SQLite | VERIFIED | MOCK-VERIFIED | MOCK-VERIFIED |
| Simulator command | SOURCE-AUDITED | SOURCE-AUDITED | NOT TESTED |
| Real robot | NOT TESTED | NOT TESTED | NOT TESTED |

The DR02 command row is deliberately not `VERIFIED`: the current preflight found an existing `arm_action_example 0 --confirm` publisher but no `/JOINTS_DATA` publisher or simulator. Its standalone process does not establish `official executable -> /JOINTS_CMD -> simulator -> motion`.

## 4. State plane and command plane

```text
STATE PLANE
===========
Robot -- telemetry --> Vendor SDK/transport --> Adapter --> Internal state/liveness

COMMAND PLANE
=============
Fleet --> RobotExecutionContext --> ??? NOT IMPLEMENTED --> Vendor command API --> Robot
```

The state plane has partial evidence shown above. The command plane is intentionally disconnected from Fleet. A standalone vendor simulator smoke test only establishes the minimum vendor command boundary; it never establishes Fleet task execution.

## 5. Why a standalone command smoke test is useful

For a vendor that has an official simulator, a clean standalone test can locate the actual command boundary before a later requirements/design phase considers an execution implementation. It must record the simulator, one command process, transport setup, publisher ownership, observed motion, and clean stop. It does **not** justify creating `DeepRoboticsExecutionContext`, `UnitreeExecutionContext`, or `AgibotExecutionContext` in this phase.

## 6. Architecture invariants

1. Fleet Registry does not depend on vendor SDKs.
2. Vendor dependencies are opt-in.
3. Telemetry arrival does not mean `IDLE`.
4. Transport liveness is not task capability.
5. Vendor transport does not enter Fleet core.
6. ROS/DDS is not required as the universal vendor integration mechanism.
7. Simulator evidence is not real-hardware evidence.
8. A command-path smoke test is not Fleet execution capability.
9. Business fields require independent provenance.
10. Adapters normalize vendor transport; they do not perform business dispatch.

## 7. Open Architecture Questions

The following are recorded, not resolved here:

- What should the heterogeneous capability model look like?
- How should task requirements be expressed?
- Are robot capabilities static, runtime-derived, or both?
- How should vendor-declared and experiment-verified capability differ?
- Can one task require multiple robots?
- Should Dispatcher know a vendor at all?
- How should command results be normalized?
- Should navigation, manipulation, and transport share one execution contract?
- How should real-hardware acceptance enter the evidence model?

No robot role, business scenario, or capability assignment is implied by this document.
