# Mobile Manipulation V1 当前仓库审计

日期：`2026-08-27`

审计对象：`inayina/amr_warehouse_navigation`（ROS package：`amr_warehouse_sim`）

分支 / HEAD：`feature/mobile-manipulation-mvp` / `c8af1cfe992591a572f5e2f51833b76e64f4437f`

审计开始时工作树：clean；该 HEAD 与 `main`、`origin/main` 同指向。

## 1. 结论先行

当前仓库提供的是一条经过源码、测试与历史 runtime 报告支撑的**单车 Gazebo / Nav2 + 固定点 + 最小 Mock WMS**链路，以及 opt-in inspection 与纯 Python Fleet 学习层。它适合作为 Mobile Manipulation 的 mobility、任务入口、导航 adapter 形状、数据 freshness 与 evidence 设计起点。

当前仓库**没有** mobile manipulator description、arm/gripper、MoveIt 2 配置、ros2_control controller、workpiece pose、manipulation adapter、base/arm interlock 或完整 Mission FSM。所有这些能力当前均为 `NOT TESTED`，不能从已安装的 ROS package、文档关键词或 inspection camera 推导为已实现。

最小风险集成方式是：保留现有 `main` 稳定入口，在本仓库内新增 opt-in ROS package boundary、world/model variant 和 launch；先复现官方 UR5e Gazebo/MoveIt baseline，再组合移动底盘，不复制另一个机械臂仓库，也不把第三方核心源码直接搬入本包。

## 2. 审计方法与证据边界

本轮检查了：

- Git branch、HEAD、工作树和最近提交；
- 根 README、`package.xml`、`setup.py`、requirements 与 Makefile；
- 全部主线 launch、Gazebo world/model、URDF、Nav2 参数、地图与任务点；
- Mock WMS SQLite/HTTP/executor/task runner；
- Fleet registry/dispatcher/haul/heartbeat/resource-lock；
- inspection FSM、Nav2 seam、camera freshness、evidence 与 tests；
- 全部 `test/`；
- 本机 ROS 2 / Gazebo / Nav2 / MoveIt 2 / ros2_control package inventory；
- ROS、Gazebo、Nav2、MoveIt、ros2_control 与 Universal Robots 官方 upstream。

本轮自动化命令 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest test -q -p no:cacheprovider` 在精确 HEAD 上得到 `187 passed in 2.27s`。这些测试主要是 static contract、fake、SQLite/FastAPI 和 simulated context，不是 Mobile Manipulation runtime，也不能替代 fresh Gazebo、MoveIt trajectory 或真机验收。

## 3. 当前能力地图

| 能力 | 当前事实 | 证据 | Mobile Manipulation 判断 |
| --- | --- | --- | --- |
| Gazebo 差速底盘 | `my_robot` 使用 Gazebo DiffDrive system，消费 `/cmd_vel`，输出 `/odom` | [`model.sdf`](../../models/my_robot/model.sdf) 319–378 | `SOURCE-AUDITED / REUSE`，但新 arm 质量、惯量与 stowed envelope 必须重验 |
| 单车仿真入口 | `simulation.launch.py` bridge `/cmd_vel /odom /scan /clock`，启动 odom TF | [`simulation.launch.py`](../../launch/simulation.launch.py) 18–80 | `SOURCE-AUDITED / KEEP`，Mobile Manipulation 使用新 variant，不原地改 |
| Nav2 入口 | saved map + AMCL + planner/controller/BT navigator | [`navigation.launch.py`](../../launch/navigation.launch.py) 22–98；[`nav2_params.yaml`](../../config/nav2_params.yaml) | `SOURCE-AUDITED / REUSE THROUGH ADAPTER` |
| Nav2 ready gate | 检查 5 个 lifecycle node、`map -> odom` 与 `/navigate_to_pose` server | [`mock_wms_executor.py`](../../amr_warehouse_sim/mock_wms_executor.py) 725–760 | `SOURCE-AUDITED / EXTEND`，还缺 arm/interlock/perception readiness |
| Nav2 Action client | 构造 stamped `PoseStamped`，处理 SUCCEEDED/ABORTED/CANCELED | [`mock_wms_executor.py`](../../amr_warehouse_sim/mock_wms_executor.py) 762–847 | 可作为 Navigation Adapter 起点，不可原样当最终 contract |
| 固定点 | `station_a` / `station_b` 为 `map` frame 点 | [`task_points.yaml`](../../config/task_points.yaml) 16–56 | 只作为 staging pose 候选；不是 manipulation calibration 或 reachability 证据 |
| Mock WMS | SQLite/CLI/FastAPI 创建、查询与状态回写单点导航任务 | [`mock_wms_db_common.py`](../../amr_warehouse_sim/mock_wms_db_common.py)；[`mock_wms_api.py`](../../amr_warehouse_sim/mock_wms_api.py) | 可作为 task ingress/status projection；schema 不能直接表达 WorkcellTask |
| Fleet | Registry、Dispatcher、haul FSM、heartbeat、resource lock | [`fleet/`](../../amr_warehouse_sim/fleet/) | `MOCK-VERIFIED`；V1 不扩展多机器人，也不把 simulated pickup 当 grasp |
| Inspection FSM/evidence | 分离 navigation、arrival、acquisition、quality、finding、fault 与 evidence | [`inspection/`](../../amr_warehouse_sim/inspection/) | 复用设计模式；inspection success 不是 manipulation success |
| RGB camera reference | 独立 inspection model 发布 simulated RGB image | [`my_robot_inspection/model.sdf`](../../models/my_robot_inspection/model.sdf) 320–368 | 可借鉴独立 variant 与 fresh-frame 机制；无 RGB-D、标定或 object pose |
| Test baseline | 本轮全量 `187 passed in 2.27s` | `.venv/bin/python -m pytest test -q -p no:cacheprovider` | `VERIFIED`，范围仅当前测试集合 |

## 4. 可以直接复用的部分

### 4.1 Mobility 与 Nav2 基线

- `maps/warehouse.yaml` 继续作为现有地图入口。
- `map -> odom -> base_link` 语义、AMCL、planner/controller/BT navigator 和固定点命名可保留。
- `RosNav2Runtime` 的 ready-gate 检查和 `NavigateToPose` goal mapping 可提炼到新 Navigation Adapter。
- 现有 navigation contract tests 可作为 Gate 0 anti-regression tests。

复用不等于沿用已有成功结论。增加 UR5e、gripper、camera 和 workpiece 后，robot footprint、重心、加减速、传感器遮挡和 staging reachability 都发生变化；旧底盘的 Nav2 `SUCCEEDED` 不能证明新 mobile manipulator 的 Gate 2。

### 4.2 上层任务入口

Mock WMS 的 CLI/HTTP/SQLite 可以继续模拟 `WMS / Operator`，但需要一个 Task Adapter 把旧单点导航 task 或新的 workcell request 转成 `WorkcellTask`。Mission 内部状态、execution attempt 和 evidence 不应继续挤进当前 `tasks.status` 一个字段。

### 4.3 可复用的设计模式

- inspection 的 `attempt_id`、freshness/provenance gate、finding 与 execution fault 分离、JSON/hash evidence；
- Fleet 文档中的业务状态、assignment 状态、execution phase 分离；
- inspection 独立 world/model/launch 的 opt-in 模式；
- ready gate 失败时 fail closed，不发送动作。

这些模式只提供结构证据。inspection 的 arrival verifier / stabilizer 在源码中明确是 deterministic mock，live runner 在导航成功后主要依赖固定 sleep；它们不能直接充当 `BASE_STATIONARY` quality gate。

## 5. 与 V1 无关或不得误用的部分

- Fleet Stage 1–5 与多品牌 vendor state adapters：V1 明确不做多机器人和 vendor command path。
- inspection 的 red-pixel rule、PASS/WARNING 业务语义：不能用于 grasp 或 trajectory quality。
- `future_extensions/` 和 `archive/`：历史/实验代码，不接回主线。
- 现有外部 MuJoCo/Panda 项目、learned policy、VLA/RL：不进入本仓 Mobile Manipulation V1。
- Dashboard / Management Plane：可以未来消费结果 projection，但不拥有本地 motion、interlock 或 safety authority。

## 6. Integration seams

| Seam | 当前一侧 | V1 新一侧 | 约束 |
| --- | --- | --- | --- |
| Task ingress | Mock WMS CLI/HTTP/SQLite | Task Adapter + WorkcellTask | 旧 schema 不反向决定 Mission schema |
| Navigation | `/navigate_to_pose` + current ready gate | Navigation Adapter | Mission 不读取 Nav2 internal plugin/BT state |
| Robot model | existing SDF base + visual URDF | composite mobile-manipulator description | 新 variant；单一 joint/TF authority |
| Base actuation | Gazebo DiffDrive plugin | unchanged in first option | 不得再由 ros2_control diff-drive 同时 claim wheels |
| Arm actuation | 无 | `gz_ros2_control` + arm/gripper controllers | controller_manager 是 arm/gripper resource owner |
| Planning | 无 | Manipulation Adapter -> MoveIt 2 | Mission 不接触 RobotTrajectory |
| Perception | inspection raw Image | Perception Adapter -> WorkpiecePose | Stage A/B/C 输出同一 contract |
| State/interlock | Nav ready only | Robot State Observer + Interlock Authority | 未知/stale state 一律拒绝动作 |
| Evidence | tests/reports + inspection artifact pattern | Mission event/evidence writer | execution truth 与 WMS projection 分离 |

## 7. 现有代码语义缺口

### 7.1 Navigation contract 不够强

当前 `ExecutorRuntime` 只有 `check_ready_gate()`、`navigate_to_pose()` 和 `close()`；没有显式 `cancel()` / `state()`。`NavigationResult` 只有 `succeeded/status/reason`。Nav2 的 `CANCELED` 被压成 `failed`；timeout 后会调用 `cancel_goal_async()`，但不验证 cancel response、最终 Action terminal state或底盘实际停止。

V1 必须新增：typed outcome、active `command_id`、cancel acknowledgement、stop confirmation、late-result fencing 和状态快照。不能让 Mission 直接复用当前 bool 结果。

### 7.2 Task ownership / concurrency 不够强

当前 SQLite `get_next_pending_task()` 和 `update_task_status()` 分离，无 `owner_id`、`execution_id`、version、lease 或 compare-and-set；HTTP status PATCH 也没有完整 transition guard。即使 V1 只允许一台机器人和一个 active task，contract 仍需携带 execution identity，防止 cancel、timeout、shutdown 后的旧 result 推进新 FSM。

### 7.3 Model 与 controller ownership 缺失

当前底盘由 Gazebo DiffDrive plugin 直接拥有 wheels；仓库没有 `<ros2_control>`、controller YAML、`joint_state_broadcaster`、`joint_trajectory_controller`、gripper controller、SRDF、kinematics 或 MoveIt controller mapping。

首选低风险方案是保留现有 base command owner，只让 `gz_ros2_control` 拥有 arm/gripper。若 Gate 1 证明 composite description 无法在该边界稳定运行，再提出受控迁移方案；不得先同时启动两个 wheel command owner再排障。

### 7.4 TF 与 perception authority 尚未定义

当前 authority：

- AMCL：`map -> odom`；
- `odom_tf_node`：`odom -> base_link`；
- static transform publisher：`base_link -> lidar frame`；
- robot_state_publisher：visual fixed joints。

V1 还需要 `base_link -> arm_base_link -> ... -> wrist_3_link`，并保留官方 UR 树中 `wrist_3_link -> flange` 与 `wrist_3_link -> tool0` 两条 sibling edge；项目 gripper/TCP 从 `flange` 向下组合为 `gripper_base_link -> mm_tcp`。此外还需要 camera、station 和 workpiece frames。每条 edge 必须只有一个 publisher。Stage A 的 Gazebo world pose 与 Nav2 `map` 的对齐也必须实测，不能假定 frame 名相同就完成标定。

### 7.5 Safety / quality 不足

当前 stable `nav2_params.yaml` 的 footprint 对应原底盘尺寸；Collision Monitor 及其 scan source 默认 disabled。仓库没有 arm-stowed envelope、base stationary、TCP/joint velocity、grasp 或 release quality gate。

Mission interlock 是系统集成防错机制，不是 functional safety。V1 文档不得把它描述为安全认证、E-stop 或保护停机等级。

## 8. 必须保持不动的现有基线

本轮和后续 Gate 的默认规则是“不修改，另建 variant”：

- `launch/navigation.launch.py`
- `launch/simulation.launch.py`
- `launch/slam.launch.py`
- `config/nav2_params.yaml`
- `config/laser_filters.yaml`
- `config/slam_toolbox.yaml`
- `maps/warehouse.yaml`、`maps/warehouse_slam.pgm`
- `models/my_robot/`、`models/my_robot_visual.urdf`
- `worlds/warehouse_full.world`
- `amr_warehouse_sim/odom_tf_node.py`
- 当前 Mock WMS / Fleet / inspection runtime 与其 tests

只有在独立 issue、明确回退方式和 Gate 0 对比证据下，才允许提议修改以上文件。Mobile Manipulation 默认新增 `mobile_manipulation_*` 资源和 launch，不替换旧文件。

## 9. 当前最大的事实冲突与 unknown

1. `station_a` / `station_b` 在配置注释中仍是 candidate/approach 语义；历史导航成功不等于机械臂可达或 base placement 已校准。
2. 当前 RGB camera 是 inspection-only，缺少 RGB-D、CameraInfo/标定链和 `WorkpiecePose` producer。
3. UR5e 官方 Gazebo simulation 的当前 branch/version matrix存在组合风险；本机虽然已安装 MoveIt/gz_ros2_control，但没有 UR description/driver/simulation package。
4. Gazebo physics grasp 可靠性未知；V1 可能需要明确标注的 DetachableJoint simulation mechanism，不能把它宣传成工业夹持。
5. 新 robot stowed footprint、重心和 station geometry 未验证，旧 Nav2 参数与地图只能作为起点。
6. 历史报告仍保留各自当时的测试数量；当前README与本审计以本轮`187 passed`为当前自动化事实，不回写历史报告中的原始数字。

## 10. 审计结论

当前代码具备清晰的 brownfield integration seams，但不具备可直接启动的 Mobile Manipulation runtime。架构工作可以结束在“需求与边界足以实现”的状态；实现必须从独立 upstream reproduction、composite model/controller ownership 和 Gate 0 live non-regression 开始，而不是先写 Mission happy path。
