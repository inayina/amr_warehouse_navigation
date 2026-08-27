# Mobile Manipulation V1 Interface Contracts

日期：`2026-08-27`

状态：**CONTRACT PROPOSAL / ROS INTERFACES NOT IMPLEMENTED**

## 1. Contract conventions

### 1.1 Identity

所有可产生 motion 或 terminal result 的 contract 必须携带：

| Field | 含义 | 规则 |
| --- | --- | --- |
| `task_id` | WMS/business intent identity | 全生命周期稳定 |
| `execution_id` | 一次 Mission execution | 每次重新 claim/recovery 新建；不可复用 |
| `attempt_id` | 某 Mission phase 的一次尝试 | bounded retry 时递增/新建 |
| `command_id` | 一个 child command | 全局唯一；Action feedback/result/cancel correlation key |
| `owner_id` | 当前 execution owner | V1 单进程也必须显式存在 |
| `state_revision` | Mission/Interlock optimistic version | transition/admission compare-and-set |

任何 identity 不匹配或 expected phase/revision 不匹配的 callback 都是 `LATE_OR_STALE_EVENT`：可以进入审计日志，不得改变当前 FSM。

### 1.2 Time

- sensor/pose/joint/odom sample：ROS time + clock domain；simulation 使用 `/clock`；
- process/network receive与timeout scheduling：steady/monotonic clock；
- persisted human-readable event：UTC wall time；
- deadline：absolute time/budget，不在每层无条件重置；
- duration不得从不兼容 clock domain相减。

### 1.3 Common outcome

```text
CommandOutcome = SUCCESS | FAILED | CANCELED | TIMEOUT
OutcomeCertainty = CONFIRMED | OUTCOME_UNKNOWN
StopState = NOT_REQUIRED | STOP_CONFIRMED | STOP_UNCONFIRMED
RetryDisposition = RETRY_ALLOWED | RETRY_REQUIRES_REVALIDATION | NO_AUTO_RETRY
```

`TIMEOUT` 描述等待预算耗尽，不自动证明底层动作已停止。`TIMEOUT + STOP_UNCONFIRMED` 必须阻止后续 motion。

## 2. A. Task Contract

### 2.1 WorkcellTask

`WorkcellTask` 表示 business intent，不保存 raw Nav2 pose或MoveIt trajectory作为唯一语义。

| Field | Type | Required | Contract |
| --- | --- | --- | --- |
| `task_id` | string | yes | 外部稳定 identity，非空/唯一 |
| `task_version` | uint64 | yes | optimistic update/version |
| `operation` | enum | yes | V1: `TRANSFER_WITH_SCAN`；其他值拒绝 |
| `pickup_station_id` | string | yes | `station_a` catalog key |
| `dropoff_station_id` | string | yes | `station_b` catalog key |
| `target_object_id` | string | yes | V1 单一标准工件 identity |
| `object_class` | string | yes | geometry/recipe lookup key |
| `recipe_id` | string | yes | scan/pick/place recipe identity |
| `recipe_version` | string | yes | immutable version used by execution |
| `valid_from` | timestamp | yes | 此前不得执行 |
| `deadline` | timestamp | yes | 过期不得开始；执行中按policy处理 |
| `priority` | enum/int | no | V1记录但不做fleet scheduling |
| `business_status` | enum | yes | 只由Task authority写 |
| `cancel_requested` | bool | yes | cancel intent，不等于CANCELED terminal fact |
| `created_at/updated_at` | timestamp | yes | provenance |

Business status：

```text
CREATED -> ACCEPTED -> IN_PROGRESS -> SUCCEEDED
                              \-----> FAILED
                              \-----> CANCELED
```

`ACCEPTED/IN_PROGRESS` 不提供 robot motion truth；`SUCCEEDED` 只能在 Mission完整 success predicate通过后由 projection写入。

### 2.2 MissionExecution

Task 与 execution 分离：

| Field | Contract |
| --- | --- |
| `execution_id` | unique per claim/run |
| `task_id/task_version` | intent snapshot correlation |
| `owner_id` | single command owner |
| `phase` | [TASK_STATE_MACHINE.md](./TASK_STATE_MACHINE.md) enum |
| `phase_revision` | CAS/fencing revision |
| `active_command_id` | none or exactly one |
| `attempt_counters` | bounded per phase |
| `started_at/deadline` | execution budget |
| `terminal_outcome` | absent until confirmed terminal |
| `outcome_certainty/stop_state` | required on failure/cancel/timeout |
| `evidence_manifest_ref` | required before success |

V1 可以先用 local persistence，但 schema 必须允许 process restart reconciliation；无法确认旧 active command时不得自动开始新的 execution。

## 3. B. Navigation Interface

### 3.1 High-level API

概念接口：

```text
navigate(NavigateCommand) -> asynchronous NavigateResult
cancel(CancelCommand) -> asynchronous CancelResult
state(StateQuery) -> NavigationStateSnapshot
```

ROS transport建议：一个 project-owned Action 用于 `navigate`，标准 Action cancel用于 active goal，另有 latched/state topic或service用于 snapshot。最终 `.action/.msg` 文件在 Gate 4 创建，本设计不把 transport name当成已实现事实。

### 3.2 NavigateCommand

| Field | Contract |
| --- | --- |
| common identities | task/execution/attempt/command/owner/state revision |
| `target_id` | station/staging semantic key |
| `target_pose` | resolved `PoseStamped` snapshot；通常 `map` frame |
| `pose_catalog_version` | staging config provenance |
| `deadline` | absolute child deadline |
| `motion_permit` | Navigation domain permit，unexpired |
| `required_arm_state` | V1 fixed `STOWED` |

### 3.3 NavigationStateSnapshot

```text
IDLE | DISPATCHING | EXECUTING | CANCELING | TERMINAL | FAULT
```

至少包含 active command identity、Nav2 goal UUID（可得时）、last feedback stamp、distance remaining（可得时）、underlying status、last result和state freshness。它不是 `BaseState`；底盘实际 stationary 由 Robot State Observer判定。

### 3.4 NavigateResult

| Field | Contract |
| --- | --- |
| common identities | 必须与active command匹配 |
| `outcome` | SUCCESS/FAILED/CANCELED/TIMEOUT |
| `fault_code` | typed fault or NONE |
| `nav2_goal_id/status` | underlying Action evidence |
| `accepted_at/terminal_at` | timestamps |
| `final_pose` | fresh pose snapshot或reference；不可伪造 |
| `stop_state` | terminal后底盘停止确认状态 |
| `certainty` | confirmed/unknown |
| `detail` | human-readable，不代替code |

### 3.5 Nav2 mapping

| Nav2 observation | Adapter result | Mission transition |
| --- | --- | --- |
| goal rejected | `FAILED + NAVIGATION_FAILED` | recovery/failed |
| GoalStatus SUCCEEDED | `SUCCESS` | 只进入 `WAIT_BASE_STATIONARY_*` |
| GoalStatus ABORTED | `FAILED + NAVIGATION_FAILED` | recovery/failed |
| GoalStatus CANCELED after correlated cancel | `CANCELED` | wait stop, then CANCELED |
| result deadline expired | begin cancel; eventually `TIMEOUT` | no next motion until stop confirmed |
| dispatch future timed out/no goal handle | `TIMEOUT + OUTCOME_UNKNOWN` | reconcile; do not resend automatically |

### 3.6 Cancel semantics

1. Mission persists `CANCEL_REQUESTED` and enters `CANCELING`.
2. Navigation Adapter checks active `command_id` and sends cancel to matching Nav2 goal。
3. Adapter records cancel response (accepted/rejected/unknown)。
4. Adapter waits correlated Action terminal state。
5. Robot State Observer confirms base quiescent。
6. Only then return `CANCELED + STOP_CONFIRMED`。
7. Deadline exceeded/rejected/no handle => `TIMEOUT or FAILED + STOP_UNCONFIRMED/OUTCOME_UNKNOWN`，Interlock remains closed。

## 4. C. Manipulation Interface

### 4.1 High-level operations

```text
scan(ManipulationCommand)
pick(ManipulationCommand)
place(ManipulationCommand)
stow(ManipulationCommand)
cancel(CancelCommand)
stop(StopCommand)
state(StateQuery) -> ManipulationStateSnapshot
```

这些是长时动作，概念上使用 ROS Actions。Mission 不接触 `MoveGroupInterface`、planner plugin、`RobotTrajectory`、FollowJointTrajectory controller或gripper controller。

### 4.2 ManipulationCommand

| Field | Contract |
| --- | --- |
| common identities | task/execution/attempt/command/owner/revision |
| `operation` | SCAN/PICK/PLACE/STOW |
| `recipe_id/version` | immutable recipe provenance |
| `target_pose` | WorkpiecePose snapshot或station-relative target；STOW可为空 |
| `target_observation_id` | target correlation；SCAN/PICK required |
| `recipe_frame` | scan/pick/place recipe的semantic reference，必须是versioned station/workpiece frame |
| `planning_frame` | MoveIt planning frame snapshot，例如combined model的world/base frame；由Adapter通过TF-at-stamp解析，不与`recipe_frame`混为一项 |
| `tool_frame` | explicit；V1 planning command使用project-defined `mm_tcp`，不把UR convention frame `tool0`误当成gripper TCP |
| `planning_scene_revision` | scene snapshot version |
| `deadline` | includes planning + execution + quality budget |
| `motion_permit` | Manipulation domain permit |
| `quality_profile_id/version` | DEMO threshold provenance |

### 4.3 Manipulation state

```text
IDLE
PLANNING
READY_TO_EXECUTE
EXECUTING
VERIFYING
CANCELING
STOPPING
TERMINAL
FAULT
```

State snapshot至少包含 active operation/identity、MoveIt planning request identity、controller goal identity、current planned/executed segment、joint/TCP sample freshness、gripper state和attached-object state。

### 4.4 ManipulationResult

```text
planning_outcome:
  status, moveit_error_code, planning_time, planner_id,
  cartesian_fraction, collision_check_enabled

execution_outcome:
  status, controller_status, started_at, terminal_at,
  final_joint_state_ref

quality_outcome:
  PASS | FAIL | NOT_EVALUATED
  position_error, orientation_error, max_joint_velocity,
  max_tcp_velocity, stable_duration, threshold_profile

domain_outcome:
  grasp = CONFIRMED | FAILED | UNKNOWN
  release = CONFIRMED | FAILED | UNKNOWN
  arm_state = STOWED | ACTIVE | FAULT | UNKNOWN

terminal:
  outcome, fault_code, retry_disposition,
  stop_state, certainty, evidence_refs
```

`plan SUCCESS + execute SUCCESS + quality FAIL` 的 overall outcome仍是 `FAILED`；pick trajectory success且grasp unknown时必须是 `GRASP_FAILED/UNKNOWN`，不能继续 transport。

### 4.5 Operation-specific rules

#### scan

- target pose fresh且TF-at-stamp可用；
- raster/line waypoints使用workpiece/station frame；
- fixed/controlled TCP orientation；
- collision checking enabled；
- Cartesian fraction达到recipe minimum；
- velocity/acceleration scaling与quality thresholds versioned；
- execution terminal后才评估tracking/stability。

#### pick

- pick前重新检查pose age；
- approach path、close、grasp confirmation、attached collision object、retreat顺序固定；
- DetachableJoint如被采用，只能在geometric/gripper preconditions通过后触发；
- attachment output与relative object pose共同作为simulation grasp evidence。

#### place

- Station B target/release region已解析；
- object仍被确认attached；
- release后attachment false、gripper open、object在acceptance region；
- release unknown禁止自动重复place。

#### stow

- named joint target由versioned config定义；
- controller result后继续读取measured joints/velocity；
- named-state error + stable duration通过才报告STOWED。

### 4.6 Cancel/stop

- `cancel` 请求底层MoveIt/controller取消并有界等待；
- `stop` 是更强的adapter-owned controller hold/stop请求，但仍不是functional safety stop；
- adapter必须确认controller terminal + measured joint/TCP quiescent；
- stop unconfirmed时Interlock保持fault/closed，Mission进入RECOVERY。

## 5. D. Perception Interface

### 5.1 High-level API

```text
observe(PerceptionRequest) -> WorkpiecePoseResult
state(StateQuery) -> PerceptionStateSnapshot
```

V1可用service或short action；provider acquisition可内部异步。Mission只认识统一结果。

### 5.2 PerceptionRequest

| Field | Contract |
| --- | --- |
| common task/execution/attempt identity | correlation |
| `object_id/object_class` | exact target selector |
| `station_id` | expected workcell |
| `preferred_output_frame` | usually `station_a_frame` |
| `maximum_age` | consumer freshness limit |
| `minimum_quality` | Stage-specific policy reference |
| `deadline` | bounded acquisition |

### 5.3 WorkpiecePose

| Field | Type/meaning |
| --- | --- |
| `observation_id` | unique observation identity |
| `object_id/object_class` | provenance |
| `header.frame_id/stamp` | pose frame + capture ROS time |
| `pose` | position + normalized quaternion |
| `covariance` | optional/Stage-specific；unknown必须显式 |
| `received_at` | adapter receive ROS/wall metadata |
| `valid_until` | policy-derived expiry |
| `quality` | PASS/LOW/INVALID/STALE |
| `confidence` | `[0,1]` only if provider defines semantics；否则unknown |
| `source` | GAZEBO_GROUND_TRUTH/FIDUCIAL/RGBD_DETECTOR |
| `source_instance/version` | provider provenance |
| `calibration_version` | camera/world-map/station alignment version |

### 5.4 Freshness and TF rules

```text
pose_valid =
    identity/provenance match
AND timestamp != zero
AND timestamp <= now
AND now <= valid_until
AND source quality policy passes
AND quaternion finite/normalized
AND transform(output <- source, observation_stamp) available
```

Perception stale maps `PERCEPTION_STALE`；TF unavailable可以使用细分 `TF_UNAVAILABLE` fault detail，但不能伪装成target unreachable。Pick consumer必须二次验证。

### 5.5 TF publication

Perception Adapter可以作为 observation-scoped `station_a_frame -> workpiece_frame`唯一authority。grasp确认后不重新parent同一个child frame；Manipulation Adapter使用独立 `carried_workpiece_frame`或MoveIt attached-object identity，避免TF authority冲突。动态TF只用于live visualization/consumer cache；可追溯的planning input必须同时持久化原始`WorkpiecePose`和exact-stamp transform snapshot，不能依赖未来仍存在的TF cache。

## 6. E. Robot / Interlock State

### 6.1 BaseStateSnapshot

```text
state = MOVING | STATIONARY | FAULT | UNKNOWN
source_stamp / received_at / valid_until
linear_speed / angular_speed
stable_since
fault_code/detail
state_revision
```

`STATIONARY` guard：fresh odometry、linear/angular speed均小于versioned threshold且连续满足stable duration。阈值初期为 `TBD-DEMO`。

### 6.2 ArmStateSnapshot

```text
state = STOWED | ACTIVE | FAULT | UNKNOWN
source_stamp / received_at / valid_until
named_state_error
max_joint_velocity / tcp_velocity
stable_since
controller_state / hardware_state
attached_object_state
state_revision
```

### 6.3 Interlock API

```text
request_permit(MotionAdmissionRequest) -> MotionPermit | AdmissionRejected
revoke(permit_id, reason)
state() -> InterlockSnapshot
```

Admission request包含motion domain、common identities、required state revisions与deadline。

拒绝映射：

| Condition | Fault |
| --- | --- |
| arm ACTIVE/unknown/stale for navigation | `ARM_NOT_STOWED` |
| base MOVING/unknown/stale for manipulation | `BASE_NOT_STATIONARY` |
| arm controller fault | `ARM_FAULT` |
| active command already exists | `COMMAND_OWNERSHIP_CONFLICT` |
| state revision changed | `INTERLOCK_STATE_CHANGED` |
| permit expired | `TIMEOUT` |

## 7. F. Fault / Result Contract

### 7.1 Required FaultCode

```text
NAVIGATION_FAILED
PERCEPTION_STALE
TARGET_UNREACHABLE
PLANNING_FAILED
EXECUTION_FAILED
GRASP_FAILED
ARM_NOT_STOWED
BASE_NOT_STATIONARY
CANCELED
TIMEOUT
ARM_FAULT
```

V1建议扩展：

```text
INVALID_TASK
TF_UNAVAILABLE
PERCEPTION_INVALID
QUALITY_GATE_FAILED
RELEASE_FAILED
CONTROLLER_UNAVAILABLE
COMMAND_OWNERSHIP_CONFLICT
STOP_UNCONFIRMED
OUTCOME_UNKNOWN
PROCESS_SHUTDOWN
EVIDENCE_PERSIST_FAILED
```

### 7.2 Fault record

| Field | Required |
| --- | --- |
| fault identity + common identities | yes |
| Mission phase / component / operation | yes |
| `FaultCode` | yes |
| `RetryDisposition` | yes |
| `OutcomeCertainty` / `StopState` | yes |
| underlying Nav2/MoveIt/controller/sensor code | when available |
| first_observed_at/last_updated_at | yes |
| evidence refs | when available |
| human detail | yes, not parsed as authority |

### 7.3 Retry policy

Adapter返回建议，最终bounded policy由Mission拥有。允许自动retry的典型条件仅包括：

- ready gate暂时未满足且没有goal sent；
- stale perception重新acquire；
- 明确只有planning失败、没有trajectory dispatch、target仍fresh且attempt budget允许。

禁止自动retry：execution failed、grasp/release unknown、arm fault、interlock violation、cancel/timeout stop unconfirmed、shutdown reconciliation unknown、pick后load state不确定。

## 8. Evidence Contract

### 8.1 ExecutionEvent

```text
event_id
task_id / execution_id / attempt_id / command_id
sequence_number / state_revision
mission_phase
event_type
source / source_version
ros_stamp / wall_stamp
result or fault summary
payload_schema_version
artifact_refs[]
previous_event_hash / event_hash (optional V1, preferred)
```

### 8.2 ArtifactReference

```text
artifact_id
media_type
relative_or_object_store_ref
sha256
size_bytes
created_at
producer
schema/version
```

Task summary只引用immutable facts/artifacts；不能用mutable latest-status row替代execution history。

## 9. Transport mapping and ownership

| Interface | Suggested ROS transport | Client | Server/owner | Underlying upstream |
| --- | --- | --- | --- | --- |
| WorkcellTask intake | CLI/HTTP adapter or ROS service | Operator/WMS | Task Adapter | current Mock WMS optional |
| Navigate | custom Action | Mission | Navigation Adapter | Nav2 NavigateToPose Action |
| Navigation state | topic/service | Mission/Interlock | Navigation Adapter | Nav2 feedback + adapter state |
| Manipulation operations | custom Action | Mission | Manipulation Adapter | MoveIt + controllers |
| Perception observe | service/short Action | Mission | Perception Adapter | Gazebo/fiducial provider |
| Robot state | topics | Mission/adapters | State Observer | odom/joints/controller state |
| Interlock permit | service + revoke event | adapters/Mission | Interlock Authority | project-owned |
| Evidence | internal API/event topic | producers | Evidence Writer | project-owned persistence |

Transport choice可以在实现时调整，但ownership、identity、typed result、timeout与cancel语义不可弱化。

## 10. Compatibility boundary with current code

- Existing `RosNav2Runtime` can supply ready-gate/Nav2 client internals, but its bool-like result与cancel behavior不满足本contract；必须wrap/extend，不能让Mission直接依赖。
- Existing Mock WMS can submit/projection task，但不能成为Mission/child-action state authority。
- Existing Fleet `RobotExecutionContext`/`SimulatedRobotContext`不包含pose、cancel、state或manipulation，不用于V1 runtime。
- Existing inspection freshness/evidence logic可参考；raw image/finding contract不等于WorkpiecePose或grasp contract。
