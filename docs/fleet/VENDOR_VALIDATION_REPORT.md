# Vendor Validation Report

日期：`2026-08-23`  
范围：三家已有 vendor 的证据审计与最小运行预检；不新增 vendor，不改 Fleet command plane。

## A. Baseline

| Item | Result |
| --- | --- |
| Main HEAD | `be00ad4c39607634db4c8b4bfb80e8f13cd09232` (`Add Unitree and Agibot vendor integrations with corresponding documentation and tests`) |
| Worktree before this documentation update | clean |
| Python baseline | `135 passed, 7 skipped in 1.19s` |
| Host ROS | Jazzy |
| Docker / official Humble isolation | Docker CLI exists, but current user cannot access its daemon |

Evidence labels used in this report are defined in [MULTI_VENDOR_ARCHITECTURE.md](./MULTI_VENDOR_ARCHITECTURE.md).

## B. DEEPRobotics state runtime

`VERIFIED` evidence already recorded in [DEEP_ROBOTICS_INTEGRATION.md](./DEEP_ROBOTICS_INTEGRATION.md): official DR02 Pro MuJoCo published `drdds/msg/Joints` on `/JOINTS_DATA`; `DeepRoboticsStateAdapter` consumed it and updated `RobotRegistry`/SQLite heartbeat while preserving `OFFLINE`, task, station, and battery fields.

The fixed official source snapshots remain:

- `deep-robotics-msg` `aa646c1782aa982f384b7e46469723f31696f778`
- `deep-robotics-sdk2` `5b5a8a82911750678d1e94fed257eebbe33f5062`
- `deep-robotics-simulation` `3e848b3b9bb725521bb1f70a3d1a2913a8d70e92`

For this audit, the official `drdds`, `deep_robotics_common`, and `dr02_pro` packages rebuilt successfully in the ignored persistent directory `vendor_audit/deep-robotics-colcon/` using Jazzy and `BUILD_SIM=ON`.

## C. DEEPRobotics command smoke test

**Result: `SOURCE-AUDITED`; not `VERIFIED`.**

The current official documents identify `arm_action_example 0 --confirm` as greeting and a supported DR02 Pro simulation path: executable -> `/JOINTS_CMD` (`drdds/msg/JointsCmd`) -> simulator. They also require exactly one command publisher.

The live preflight on `ROS_DOMAIN_ID=42` found:

| Measurement | Observation |
| --- | --- |
| Existing command process | `/opt/ros/jazzy/bin/ros2 run dr02_pro arm_action_example 0 --confirm`, started before this audit |
| `/JOINTS_CMD` | 1 publisher (`/arm_action_example`), 0 subscribers |
| `/JOINTS_DATA` | 0 publishers; only the existing command example and diagnostic subscriber |
| Simulator process | absent at preflight |
| Motion observation / clean stop | not available |

This is a safety stop. No second command publisher was started, and the pre-existing process was not terminated. The desired end-to-end command smoke therefore remains unverified; it must be rerun only after the existing publisher is intentionally stopped by its owner and a simulator is demonstrably publishing `/JOINTS_DATA`.

## D. Unitree environment

Official fixed source snapshots:

- `unitree_sdk2` `9754cd153af3da471b0fe5f3aa535e426fb11db3`
- `unitree_ros2` `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88`
- `unitree_mujoco` `ae6a8403e272733e9996ef59990880330496177f`

Official sources identify simulation as Go2 MuJoCo with native SDK2 DDS `rt/lowstate`, domain `1`, interface `lo`; the ROS-side contract is `/lowstate` with `unitree_go/msg/LowState`. The documented ROS environments are Foxy/Humble (Humble recommended) with `rmw_cyclonedds_cpp`.

Current host is Jazzy and has neither `unitree_go`, `rmw_cyclonedds_cpp`, a Unitree simulator executable, nor Python `unitree_sdk2py`. Docker exists but its daemon is unavailable to the current user, so an isolated official Humble runtime could not be started without a new environment authorization.

## E. Unitree telemetry runtime

**Result: `SOURCE-AUDITED`.** The source-to-adapter path is audited, and the local adapter’s fake-message contract is `MOCK-VERIFIED`; no valid claim exists for Go2 MuJoCo -> native DDS -> ROS 2 `/lowstate` -> adapter -> SQLite on this Jazzy host.

Consequently there are no runtime measurements for Unitree node list, endpoint QoS, rate, echo, type delivery, adapter callback, or SQLite before/after. “Jazzy compatibility” remains unverified.

## F. Unitree command smoke test

**Result: `SOURCE-AUDITED`.** Official `unitree_mujoco/example/python/stand_go2.py` is the applicable command example and initializes SDK2 with simulation domain `1` and `lo`. It was not run because telemetry runtime is not available; no custom `LowCmd` was written and nothing was connected to Fleet.

## G. Agibot compile/link/mock boundary

Official D1 MaxPro SDK snapshot: `7828aef8238388c11267e56d5e44bac9f6dd2eb4`.

| Boundary | Result |
| --- | --- |
| `createQuadruped()` symbol | VERIFIED in official `libhigh_level_remote_tcp_client.so` |
| `RobotProxy::GetRobotStatus()` symbol | VERIFIED in official library |
| Local state probe compile/link | VERIFIED |
| Loader resolution | VERIFIED: probe RUNPATH resolves the official `.so` under `vendor_audit/agibot-audit/.../build` |
| Probe JSONL -> adapter mock IPC | MOCK-VERIFIED |
| Real SDK TCP/network initialization | NOT TESTED |
| Official simulator / real robot | NOT TESTED |

No fake TCP server or fake Agibot simulator was introduced.

## H. Evidence matrix

| Vendor | Code | Unit | Compile | Simulator telemetry runtime | Command runtime | Real robot |
| --- | --- | --- | --- | --- | --- | --- |
| DEEPRobotics DR02 Pro | VERIFIED | VERIFIED | VERIFIED | VERIFIED | SOURCE-AUDITED | NOT TESTED |
| Unitree Go2 | VERIFIED | MOCK-VERIFIED | VERIFIED | SOURCE-AUDITED | SOURCE-AUDITED | NOT TESTED |
| Agibot D1 MaxPro | VERIFIED | MOCK-VERIFIED | VERIFIED | NOT TESTED | NOT TESTED | NOT TESTED |

## I. Failures encountered

1. The restricted executor blocks local ROS 2 DDS/XML-RPC sockets. The read-only ROS graph audit therefore required approved local loopback execution; this was a sandbox restriction, not vendor transport failure.
2. The first isolated DR02 build selected a user-local Python 3.11 without `catkin_pkg`. Rebuilding with `-DPython3_EXECUTABLE=/usr/bin/python3` (3.12) completed.
3. The requested DR02 command smoke safety gate found an existing command publisher with no simulator peer. It was not disturbed.
4. Unitree lacks its documented Humble/CycloneDDS environment and a usable Docker daemon on this host.

## J. Fixes

Only the isolated build invocation was corrected: it used `-DPython3_EXECUTABLE=/usr/bin/python3`. No vendor checkout, Fleet core, Nav2 baseline, or application code was changed.

## K. Remaining NOT TESTED

- DR02 Pro real robot and a clean, standalone simulator command round-trip.
- Unitree Go2 simulator telemetry, ROS bridge endpoint QoS/rate, adapter/SQLite runtime, simulator stand/down, and real robot.
- Agibot real SDK network init, real robot telemetry, and command path.

## L. Architecture conclusions

The current supported conclusion is **multi-vendor state integration experiment**, not heterogeneous fleet execution. The actual stable internal seam is validated liveness arrival -> `record_heartbeat(recover_offline=False)`. The command boundary belongs to a later requirements/design phase; its open questions are recorded in [MULTI_VENDOR_ARCHITECTURE.md](./MULTI_VENDOR_ARCHITECTURE.md).
