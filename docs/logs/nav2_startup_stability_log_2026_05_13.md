# Nav2 Startup Stability Diagnostic Log

Date: `2026-05-13`

Source note: this run follows the diagnostic direction in
[nav2_startup_stability_notes.md](./nav2_startup_stability_notes.md), with one correction from live observation: only publishing `start_zone` initial pose is not enough to exercise the navigation chain, so each counted round also sends one diagnostic `candidate_dock_a` goal probe.

Scope:

- No changes were made to `navigation.launch.py`.
- No changes were made to `config/nav2_params.yaml`.
- No changes were made to maps, world, robot model, or `config/task_points.yaml`.
- The diagnostic goal is not counted as navigation-point retesting. It is only used to observe whether the startup chain is ready to accept and execute a Nav2 action.

## Protocol

Each counted round used a fresh session:

1. Stop ROS daemon and clean leftover Nav2 / Gazebo / bridge / robot state / odom TF processes.
2. Launch:
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
3. Record state near `T+10s` and `T+20s`.
4. Publish initial pose:
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
5. Record state near `T+30s`.
6. Send one diagnostic goal probe to `candidate_dock_a`:
   `map: x=0.0, y=-3.8, yaw=-1.57`
7. Record state near `T+45s` and `T+60s`.

READY definition for this log:

- `/map_server`, `/amcl`, `/planner_server`, `/controller_server`, `/bt_navigator` are all `active [3]`
- `/navigate_to_pose` reports `Action servers: 1`
- `map -> odom` is observed by short `tf2_echo`

Goal result is recorded separately from READY / NOT_READY.

## Discarded Attempts

- One initial-only diagnostic was run before the correction. It is not counted because no goal probe was sent.
- One attempted goal probe was discarded because pre-clean inspection showed leftover launch / Gazebo / Nav2 processes from a previous session. It was not a valid fresh session.

## Round Timeline

### GOAL-PROBE-01

Start time: `2026-05-13T14:57:35+08:00`

| Time | Key node presence | Lifecycle state | Action server | TF `map -> odom` | Notes |
| --- | --- | --- | --- | --- | --- |
| `T+10s` | Key Nav2 nodes not yet visible in `ros2 node list` | all queried key nodes returned `Node not found` | `0` | `no` | startup still incomplete |
| `T+20s` | key nodes visible | `/map_server active [3]`, `/amcl active [3]`, `/controller_server active [3]`, `/planner_server inactive [2]`, `/bt_navigator inactive [2]` | `1` | `no` | action server appeared while navigation lifecycle was still incomplete |
| initial pose | `/initialpose` had `1` subscriber | published `10/10` messages | N/A | N/A | `start_zone` was published successfully |
| `T+30s` | key nodes visible | same as `T+20s`; `/planner_server` and `/bt_navigator` still `inactive [2]` | `1` | `yes` | initial pose restored TF, but did not complete lifecycle |
| goal probe | N/A | lifecycle still incomplete before send | action server available | TF available | goal was rejected |
| `T+45s` | key nodes visible | `/planner_server inactive [2]`, `/bt_navigator inactive [2]` | `1` | `yes` | no post-goal lifecycle recovery observed |
| `T+60s` | key nodes visible | `/planner_server inactive [2]`, `/bt_navigator inactive [2]` | `1` | `yes` | still not ready |

Final判定: `NOT_READY`

Observed goal result: `REJECTED`

### GOAL-PROBE-02

Start time: `2026-05-13T15:04:05+08:00`

| Time | Key node presence | Lifecycle state | Action server | TF `map -> odom` | Notes |
| --- | --- | --- | --- | --- | --- |
| `T+10s` | partial node visibility | lifecycle discovery incomplete; `/bt_navigator` reported `unconfigured [1]` | `0` | `no` | startup still in progress |
| `T+20s` | key nodes visible | `/map_server active [3]`, `/amcl active [3]`, `/controller_server active [3]`, `/bt_navigator inactive [2]`; `/planner_server` query returned no stable state in the captured line | `1` | `no` | action server appeared before full readiness |
| initial pose | `/initialpose` had `1` subscriber | published `10/10` messages | N/A | N/A | `start_zone` was published successfully |
| `T+30s` | key nodes visible | all five key lifecycle nodes were `active [3]` | `1` | `yes` | reached READY before sending the diagnostic goal |
| goal probe | N/A | all five key lifecycle nodes were active before send | action server available | TF available | goal accepted |
| `T+45s` | key nodes visible | all five key lifecycle nodes were `active [3]` | `1` | `yes` | readiness persisted after goal execution |
| `T+60s` | key nodes visible | all five key lifecycle nodes were `active [3]` | `1` | `yes` | still ready |

Final判定: `READY`

Observed goal result: `SUCCEEDED`

### GOAL-PROBE-03

Start time: `2026-05-13T15:12:58+08:00`

| Time | Key node presence | Lifecycle state | Action server | TF `map -> odom` | Notes |
| --- | --- | --- | --- | --- | --- |
| `T+10s` | partial node visibility | `/map_server active [3]`, `/amcl active [3]`, `/controller_server active [3]`, `/bt_navigator inactive [2]`; some node-list checks still incomplete | `1` | `no` | action server was visible early while TF was not ready |
| `T+20s` | key nodes visible | `/amcl active [3]`, `/controller_server active [3]`, `/bt_navigator inactive [2]`; some captured lifecycle lines were blank under command timeout | `1` | `no` | still not ready before initial pose |
| initial pose | `/initialpose` had `1` subscriber | published `10/10` messages | N/A | N/A | `start_zone` was published successfully |
| `T+30s` | key nodes visible | all five key lifecycle nodes were `active [3]` | `1` | `yes` | reached READY before sending the diagnostic goal |
| goal probe | N/A | all five key lifecycle nodes were active before send | action server available | TF available | goal accepted |
| `T+45s` | key nodes visible | all five key lifecycle nodes were `active [3]` | `1` | `no` in the short check | lifecycle and action stayed ready; short TF check did not observe `map -> odom` in this sample |
| `T+60s` | key nodes visible | all five key lifecycle nodes were `active [3]` | `1` | `yes` | TF was observed again |

Final判定: `READY`

Observed goal result: `ABORTED`

## Summary

| Metric | Count | Ratio |
| --- | --- | --- |
| Counted fresh sessions | `3` | `100%` |
| READY | `2` | `66.7%` |
| NOT_READY | `1` | `33.3%` |
| Goal accepted | `2` | `66.7%` |
| Goal rejected | `1` | `33.3%` |
| Goal succeeded | `1` | `33.3%` |
| Goal aborted | `1` | `33.3%` |

## Observed Patterns

- Publishing initial pose restored `map -> odom` in the NOT_READY round, but it did not move `/planner_server` or `/bt_navigator` from `inactive [2]` to `active [3]`.
- `/navigate_to_pose` can report `Action servers: 1` before the full lifecycle precondition is satisfied.
- In the two READY rounds, readiness was reached by the first post-initial-pose sample near `T+30s`, before the diagnostic goal was sent.
- Sending the diagnostic goal did not convert the NOT_READY round into READY. In GOAL-PROBE-01, the goal was rejected and lifecycle stayed incomplete.
- Goal result and startup readiness are related but not identical. GOAL-PROBE-03 reached READY, accepted the goal, but the goal ended as `ABORTED`.

## Diagnostic Conclusion

The three counted fresh sessions show startup readiness instability under the corrected protocol:

- `2/3` sessions reached the full precondition set within the observed window.
- `1/3` sessions did not reach full lifecycle readiness even after initial pose and a diagnostic goal attempt.
- The clearest recurring unstable point is still lifecycle convergence, especially `/planner_server` and `/bt_navigator` remaining `inactive [2]` in the NOT_READY round.

No root cause is assigned in this log.
