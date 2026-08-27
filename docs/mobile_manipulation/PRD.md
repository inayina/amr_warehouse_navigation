# Mobile Manipulation V1 PRD

日期：`2026-08-27`

状态：**PROPOSED / NOT IMPLEMENTED / NOT TESTED**

## 1. 产品定义

在现有 AMR Warehouse Navigation 项目中，以 opt-in 方式增加一个“感知驱动的移动操作机器人多工位作业参考系统”。V1 用单台差速底盘、单 UR5e-class 机械臂、两指平行夹爪和模拟相机，在 Gazebo Harmonic 中完成 Station A 到 Station B 的确定性 workpiece transfer vertical slice。

本项目的首要价值不是展示复杂抓取算法，而是证明以下软件责任可以通过明确 contract、ownership、interlock、timeout、fault 和 evidence 正确组合：

```text
task intent
-> navigation
-> base stationary quality
-> perception + TF
-> scan / manipulation planning
-> trajectory execution quality
-> grasp / release confirmation
-> stow / transport interlock
-> result persistence
```

## 2. 目标用户与展示目标

主要受众：

- 机器人运动控制 / ROS 2 软件工程师面试官；
- 机器人系统架构 / 系统集成工程师面试官；
- 希望复核代码、测试、runtime evidence 与 claim boundary 的工程团队。

希望证明：

- 能在 brownfield ROS 2 系统中识别稳定基线与 integration seam；
- 能使用 Nav2、MoveIt 2、TF、ros2_control 的既有能力，而不是重造底层框架；
- 能定义跨进程任务、动作、状态、错误、取消与证据合同；
- 能把 navigation result、physical state、planning result、execution result 和业务 success 分开；
- 能以 Gate 和 fault injection 收敛复杂系统，而不是只完成 happy path demo。

## 3. V1 场景

### 3.1 环境与机器人

- Warehouse world 中增加独立的 Mobile Manipulation variant；
- Station A：一个标准、单一、已知几何的 workpiece/料盒；
- Station B：一个标准放置区域；
- 单台差速移动底盘；
- 单 UR5e-class 6-DoF arm，最终型号由 upstream baseline 决策确认；
- 简单两指平行夹爪；
- 一台 simulated RGB camera，Stage B 可切换到 fiducial；RGB-D 不进入 V1 completion；
- ROS 2 Jazzy、Gazebo Harmonic、Nav2、MoveIt 2、ros2_control。

### 3.2 完整 vertical slice

1. Operator / Mock WMS 创建 `WorkcellTask`。
2. Mission 接受任务并创建唯一 `execution_id`。
3. Interlock 确认 arm measured state 为 `STOWED`，Navigation Adapter 才能向 Nav2 发 Station A staging goal。
4. Nav2 返回 `SUCCESS` 后，Mission 进入 `WAIT_BASE_STATIONARY_A`，使用 fresh odometry/twist 与 stable duration 判断底盘稳定。
5. Perception Adapter 获取目标 workpiece pose，校验 timestamp、source、quality 与 TF-at-stamp。
6. Manipulation Adapter 生成并执行一段固定 orientation、低速、collision-checked raster/line scan。
7. Quality Gate 检查 path completion、position/orientation error、joint/TCP velocity 与 stable duration；MoveIt success 单独不足以通过。
8. 若 pick 前 pose 已过期，重新 perception；不得沿用 stale target。
9. Manipulation Adapter 执行 deterministic pick。
10. 独立 grasp confirmation 通过后，arm 执行 stow。
11. 只有 measured `ArmState.STOWED` 后，Interlock 才允许底盘前往 Station B。
12. Nav2 到达 Station B，Mission 再次确认 base stationary。
13. Manipulation Adapter 执行 place，独立确认 release。
14. arm 执行 final stow。
15. 全部 required evidence 持久化后，task 才进入 `COMPLETED/SUCCESS`。

## 4. V1 成功定义

任务成功必须是以下事实的合取，而不是某个子系统返回 `SUCCESS`：

```text
task_success =
    nav_to_station_a == SUCCESS
AND base_stationary_a == PASS
AND workpiece_pose_quality == PASS
AND scan_execution == SUCCESS
AND scan_quality == PASS
AND pick_execution == SUCCESS
AND grasp_confirmation == PASS
AND stow_after_pick == PASS
AND nav_to_station_b == SUCCESS
AND base_stationary_b == PASS
AND place_execution == SUCCESS
AND release_confirmation == PASS
AND final_stow == PASS
AND required_evidence_persisted == true
AND no_unresolved_active_command == true
```

任何 `UNKNOWN`、stale state、stop unconfirmed 或 evidence conflict 都不能写成 task success。

## 5. V1 范围

### 5.1 必须包含

- `WorkcellTask` / `MissionExecution` 明确合同；
- Navigation、Manipulation、Perception、Robot State/Interlock adapters；
- typed result 与 fault code；
- sequential Mission FSM；
- `map -> odom -> base_link -> arm_base_link -> ... -> wrist_3_link`，以及官方 UR `flange/tool0` sibling frames、项目 gripper/TCP/camera TF chain；
- camera、station、workpiece frame authority；
- Nav2 到 Station A/B；
- base stationary admission；
- Stage A Gazebo pose provider；
- deterministic scan；
- execution quality gate；
- deterministic pick/place 与 simulated grasp/release confirmation；
- arm stow / navigation interlock；
- cancel、timeout、shutdown 和 late-result isolation；
- three mandatory fault cases；
- per-gate test/report/evidence。

### 5.2 可替换但 contract 不变

- Stage A Gazebo pose -> Stage B fiducial pose；
- UR5e simulation package patch level；
- simple parallel gripper implementation；
- scan recipe parameters；
- task ingress 可以来自 test fixture、CLI 或 Mock WMS adapter。

## 6. 明确 non-goals

- LLM task planner、VLA、imitation learning、RL grasp 或复用未通过 grasp gate 的 learned policy；
- 双臂、机器狗、humanoid、多机器人调度扩展；
- whole-body simultaneous base+arm planning；
- complex bin picking、advanced learned 6D pose、CAD 自由曲面加工；
- force control、impedance/admittance、advanced manipulability optimization；
- 真实 PLC / industrial I/O；
- Isaac Sim 或 MuJoCo runtime；
- 真实硬件、Sim2Real、functional safety certification、工业节拍或精度声明；
- 大规模改写现有 Nav2、SLAM、Mock WMS、Fleet 或 inspection 主线；
- 为关键词而引入 BehaviorTree.CPP。V1 使用可审计 FSM；BT 只作为后续评估项。

## 7. 关键产品约束

### 7.1 Fail closed

- arm state unknown/stale/non-stowed：拒绝 navigation；
- base state unknown/stale/non-stationary：拒绝 manipulation；
- workpiece pose stale/invalid/TF unavailable：拒绝 scan/pick；
- active child command 未确认终止：不启动下一个动作；
- cancel/timeout 后 stop unconfirmed：进入 recovery-required fault，不释放 motion ownership。

### 7.2 Evidence bounded

- Gazebo task success 只称 simulation runtime evidence；
- DetachableJoint 或 ground-truth grasp 只称 deterministic simulation mechanism；
- MoveIt planning 与 trajectory execution 分开记录；
- grasp/release 必须有独立 confirmation；
- threshold 在实测前标记 `DEMO THRESHOLD`；
- 不产生真机、工业现场、安全认证或性能指标 claim。

### 7.3 Baseline isolation

Mobile Manipulation 的 launch、description、MoveIt config、mission 与 tests 必须 opt-in。运行现有 `navigation.launch.py` 时，不应启动 arm controller、MoveIt、perception、Mission 或新 workcell objects。

## 8. 用户可见结果

一次 accepted V1 run 至少产出：

- task/execution/attempt/command correlation IDs；
- 每个 Mission transition 的时间、trigger、state revision；
- Nav2 goal/result 与 final pose reference；
- stationary gate inputs/result；
- WorkpiecePose snapshot、source、stamp、age、frame 与 transform metadata；
- MoveIt plan result、execution result 与 quality metrics；
- grasp/release/stow state evidence；
- cancel/timeout/fault events；
- task summary JSON 和 artifact hashes。

## 9. V1 验收场景

### 9.1 Happy path

单个标准 workpiece 从 Station A 被扫描、拾取、stow 后运输到 Station B，完成放置、release、final stow，并生成一致 evidence。

### 9.2 Mandatory fault cases

1. `workpiece pose stale`：不得启动 manipulation，不得进入 `PICKING`。
2. `arm not STOWED while navigation requested`：admission rejected，底盘不得开始移动。
3. `trajectory execution failed`：Mission 不得进入下一阶段，不得写 task success，必须记录 typed fault。

### 9.3 Additional evaluated cases

Nav2 failure、cancel during manipulation、grasp failure、planning failure、shutdown、cancel result race、pose 在 scan 后过期。V1 是否全部实现由 Gate 7 范围决定，但 contract 必须先定义。

## 10. Open decisions

以下均不是已解决事实：

- 官方 UR simulation 的具体 pin 与 composite mounting 方法；
- simple gripper 的模型/controller 与 mimic joint 方案；
- Gazebo physics-only grasp 还是明确的 DetachableJoint simulation mechanism；
- Station A/B manipulation geometry 与 staging pose；
- `DEMO THRESHOLD` 数值；
- camera eye-in-hand 的最终 mounting/extrinsic；
- workpiece pose covariance/confidence 的 Stage A 语义；
- base actuation长期保留 Gazebo DiffDrive 还是迁移 ros2_control。

这些 decision 必须在对应 Gate 用运行证据关闭，不得在文档中写成已验证。
