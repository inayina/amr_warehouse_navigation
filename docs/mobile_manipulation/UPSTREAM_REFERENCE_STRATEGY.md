# Mobile Manipulation V1 Upstream / Reference Strategy

日期：`2026-08-27`

状态：**SOURCE-AUDITED / UPSTREAM BASELINES NOT REPRODUCED**

## 1. Decision

不选择一个“大一统 mobile manipulator 仓库”整体复制或fork。V1采用组合式二次开发：

```text
current AMR / Nav2 baseline
        +
Universal Robots official description / simulation
        +
MoveIt 2 + ros2_control + gz_ros2_control
        +
simple project-owned parallel gripper
        +
project-owned adapters / Mission / Interlock / Evidence
```

当前没有找到并运行一个同时满足“本仓差速底盘 + UR5e + ROS 2 Jazzy + Gazebo Harmonic + MoveIt 2”的官方单仓baseline。因此组合兼容性仍为 `NOT TESTED`；这正是 Gate 0/1 要关闭的integration risk。

## 2. Platform compatibility baseline

官方兼容依据：

- [ROS 2 REP-2000](https://www.ros.org/reps/rep-2000.html)：Jazzy 的Tier-1平台与支持周期；
- [Gazebo ROS compatibility](https://gazebosim.org/docs/latest/ros_installation/)：ROS 2 Jazzy与Gazebo Harmonic的推荐配对；
- [gz_ros2_control Jazzy documentation](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html)：Jazzy binary、Harmonic integration、arm/controller与mimic gripper examples；
- [MoveIt Setup Assistant](https://moveit.picknik.ai/main/doc/examples/setup_assistant/setup_assistant_tutorial.html) 与 [Move Group Interface](https://moveit.picknik.ai/main/doc/examples/move_group_interface/move_group_interface_tutorial.html)：robot-specific MoveIt config、planning/execution/Cartesian path边界；
- [Nav2 documentation](https://docs.nav2.org/)：Navigation Action与bringup authority。

### 2.1 Current host inventory

本轮只读核对：

| Component | Installed on host | Evidence meaning |
| --- | --- | --- |
| ROS distro | Jazzy | `VERIFIED` environment identity only |
| Gazebo Sim | `8.10.0` | binary version only |
| Nav2 | `1.3.10` | package presence; existing AMR runtime有历史证据 |
| MoveIt 2 | `2.12.4` | package presence only；本仓未运行 |
| ros2_control | `4.44.0` | package presence only；本仓未配置 |
| ros2_controllers | `4.39.0` | package presence only |
| gz_ros2_control | `1.2.17` | package presence only |
| ros_gz | `1.0.18` | package presence；current AMR使用 |
| UR packages | not installed | `NOT TESTED` |

`package installed` 不等于本仓model/controller/ABI组合已验证。

## 3. Official candidate pins

以下是 `2026-08-27` 由官方release/tag或远端核对的**候选版本快照**。它们用于建立可复现manifest，不代表本仓已经选择、安装或运行。

| Layer | Official repository | Tag | Commit snapshot | Candidate baseline / assumptions |
| --- | --- | --- | --- | --- |
| Nav2 | [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2) | `1.3.12` | `6be3614013ec` | current host仍为1.3.10；不得为了MM顺便改变stable Nav2 |
| MoveIt 2 | [moveit/moveit2](https://github.com/moveit/moveit2) | `2.12.4` | `1ade0e9dcf50` | matches installed semantic version |
| ros2_control | [ros-controls/ros2_control](https://github.com/ros-controls/ros2_control) | `4.45.2` | `4324cabf03a1` | current host 4.44.0；avoid partial upgrades |
| ros2_controllers | [ros-controls/ros2_controllers](https://github.com/ros-controls/ros2_controllers) | `4.40.1` | `31015e0aa7ce` | current host 4.39.0 |
| Gazebo control | [ros-controls/gz_ros2_control](https://github.com/ros-controls/gz_ros2_control) | `1.2.19` | `3632af299889` | current host 1.2.17 |
| ROS–Gazebo | [gazebosim/ros_gz](https://github.com/gazebosim/ros_gz) | `1.0.22` | `d1e1ef032289` | current host 1.0.18 |
| UR driver / MoveIt example | [UniversalRobots/Universal_Robots_ROS2_Driver](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver) | `3.8.0` | `409548c71b12` | Jazzy release；UR arm-only MoveIt example |
| UR description | [UniversalRobots/Universal_Robots_ROS2_Description](https://github.com/UniversalRobots/Universal_Robots_ROS2_Description) | `3.5.1` | `710505166d03` | Jazzy release；xacro/meshes/frames |
| UR Gazebo simulation | [UniversalRobots/Universal_Robots_ROS2_GZ_Simulation](https://github.com/UniversalRobots/Universal_Robots_ROS2_GZ_Simulation) | `2.5.0` | `048c80cd1faf` | standalone Gazebo/controller/MoveIt baseline |

Gate 0必须先选择一种一致策略：

1. freeze current host package snapshot并安装与其兼容的UR packages；或
2. 在隔离workspace/container中受控更新整套candidate snapshot。

禁止只升级一个control/MoveIt package后，把ABI/behavior差异归咎于本仓代码。任何安装/更新是Gate 1实施动作，需要用户明确授权。

## 4. Upstream reproduction ladder

所有reproduction在隔离workspace/container先执行，不在本仓launch中直接include standalone upstream launch。

### Baseline U0: Nav2 reference smoke

```bash
ros2 launch nav2_bringup tb3_simulation_launch.py headless:=False
```

目的：确认candidate environment的Jazzy/Harmonic/Nav2基本组合；不替代本仓现有Nav2 Gate 0。

### Baseline U1: UR5e + gz_ros2_control

```bash
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur5e
```

保存：exact versions、active `/controller_manager`、joint state broadcaster、trajectory controller、TF tree、known joint command result。这里只验证standalone arm control，不验证MoveIt或grasp。

### Baseline U2: UR5e + MoveIt

```bash
ros2 launch ur_simulation_gz ur_sim_moveit.launch.py ur_type:=ur5e
```

保存：known joint goal plan + execute、MoveIt/controller mapping、planning scene、terminal controller state。Planning success与execution success分别记录。

### Baseline U3: Parallel mimic gripper

```bash
ros2 launch gz_ros2_control_demos gripper_mimic_joint_example_position.launch.py
```

参考 [gripper controller](https://control.ros.org/jazzy/doc/ros2_controllers/gripper_controllers/doc/userdoc.html) 与 [gz_ros2_control demos](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html)。Jazzy优先研究 `parallel_gripper_action_controller/GripperActionController`；不要从旧single-DOF API猜当前合同。

### Baseline U4: Camera bridge

复现官方 `ros_gz_sim_demos` camera/RGBD示例，确认image、camera_info、可选depth与ROS time。V1不要求point cloud或Stage C detector。

每个baseline未通过即stop；不得跳到combined model靠大量patch掩盖upstream问题。

## 5. Why official UR standalone launch is reference-only

[UR GZ `ur_sim_control.launch.py`](https://github.com/UniversalRobots/Universal_Robots_ROS2_GZ_Simulation/blob/2.5.0/ur_simulation_gz/launch/ur_sim_control.launch.py) 自己启动：

- Gazebo；
- robot_state_publisher；
- `/clock` bridge；
- global `/controller_manager`；
- entity `ur`。

本仓 `simulation.launch.py` 已拥有Gazebo、clock bridge与base/TF bringup。直接include两套launch会造成process、topic、controller、entity或TF authority冲突。

最终策略：

- standalone launch只用于U1/U2复现；
- combined bringup由本仓统一拥有one Gazebo、one `/clock` authority、one combined robot_state_publisher和明确controller manager；
- 复用UR xacro macro、meshes、controller parameters与MoveIt config pattern，不复用整个standalone process graph。

## 6. UR frame reality and project delta

用户给出的概念链 `... -> flange -> tool0` 不应直接变成实现假设。官方 [UR Robot Frames](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_description/doc/robot_frames.html) 显示：

```text
UR base_link
├── base
└── base_link_inertia
    └── ...
        └── wrist_3_link
            ├── tool0
            └── flange
```

`flange` 与 `tool0` 是siblings；`base` 与`base_link`也存在UR convention差异。V1建议组合树：

```text
mobile base_link
└── arm_mount_link
    └── UR base_link / base / base_link_inertia / ... / wrist_3_link
        ├── tool0
        └── flange
            └── gripper_base_link
                └── mm_tcp
                    └── camera_link
                        └── camera_optical_frame
```

实际prefix和link names在Gate 1 xacro spike后冻结。MoveIt end-effector/TCP优先使用project-defined `mm_tcp`，不虚构 `flange -> tool0` edge，也不修改upstream core来迎合示意图。

## 7. MoveIt reuse boundary

UR官方文档说明 `ur_moveit_config` 是arm-only example，复杂workcell应创建自己的description/MoveIt config：[Custom workcell tutorial](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_tutorials/my_robot_cell/doc/index.html)。

本仓应：

- 新建combined MoveIt config；
- planning group只含arm，gripper为end-effector group；
- 不建立whole-body planning group；
- 把base、mount、camera、gripper与workcell collision加入robot/planning scene；
- base stationary后才plan；
- 显式选择controller mapping、Trajectory Execution Monitoring、goal tolerance与timeout。

UR example对scaled controller可能默认关闭Trajectory Execution Monitoring；本仓Gazebo使用标准joint trajectory controller时不能不经审查照搬该选择。

[MoveIt mobile base + arm tutorial](https://moveit.picknik.ai/humble/doc/examples/mobile_base_arm/mobile_base_arm_tutorial.html) 只作为“navigation交给Nav2、manipulation交给MoveIt”的架构旁证；它是Humble/Stretch reference，不是Jazzy/UR5e executable baseline。

## 8. Gripper and simulation grasp

### 8.1 V1 preferred gripper

项目内最小parallel-jaw xacro + mimic joint + standard parallel gripper controller。这样避免第一版引入未验证的hardware driver，同时保留future adapter boundary。

Robotiq官方 [robotiq/ros](https://github.com/robotiq/ros) 可作为future hardware contract reference，但本轮没有官方且已复现的“UR5e + Robotiq + Gazebo Harmonic”组合，因此不是Gate 1 dependency。

### 8.2 Grasp mechanism

`gripper reached goal` 只证明joint/controller目标，不证明object被抓住。

Gazebo [DetachableJoint](https://gazebosim.org/api/sim/8/detachablejoints.html) 可detach/reattach配置期指定的child model，但其initial attachment与dynamic-use assumptions需要单独spike。若采用：

- 组件命名为 `SimulationGraspAdapter`；
- attach前仍检查geometry、gripper close与pose；
- output state进入grasp evidence；
- claim只能是deterministic simulation attachment，不能是industrial grasp。

若DetachableJoint不满足“工件初始自由、pick时附着”，Gate 6必须在physics-only与最小project plugin之间做明确ADR；不得无来源引入classic Gazebo link-attacher。

## 9. Reference architecture, not dependency

Clearpath官方Jazzy/Harmonic manipulation tutorial展示了combined robot config生成、Gazebo controllers与独立MoveIt bringup：[Clearpath manipulation in Gazebo](https://docs.clearpathrobotics.com/docs/ros/tutorials/manipulation/gazebo/)。其A200/Kinova/generator/namespace contract与本仓不同，因此只借鉴package/launch/controller ownership，不复制或依赖。

Stretch官方current simulation主要面向Humble/MuJoCo，不符合Jazzy/Harmonic和本项目non-goal，不选。

## 10. Requirement delta before integration

U0–U4复现后必须形成表：

| Concern | Upstream behavior | Project requirement | Delta | Decision |
| --- | --- | --- | --- | --- |
| Gazebo owner | UR launch owns simulator | current AMR bringup owns one simulator | process conflict | reuse xacro, custom bringup |
| base command | current DiffDrive plugin | preserve stable base | none forGate 1 | keep owner |
| arm control | UR standalone controller manager | combined arm/gripper only | namespace/resource delta | adapter/config |
| robot description | arm-only | mobile base + mount + gripper + camera | composite model | project description package |
| MoveIt config | arm-only example | workcell collision + custom TCP | config delta | project MoveIt config |
| task execution | none | typed Mission contracts | new domain | project adapters/FSM |
| grasp | no project workpiece contract | deterministic simulation confirmation | gap | SimulationGraspAdapter spike |

## 11. Reuse / adapter / patch policy

Direct reuse：Nav2 Action、MoveIt planning/execution APIs、FollowJointTrajectory、ParallelGripperCommand、UR description macro/meshes、ros_gz与gz_ros2_control。

Project adapters：Navigation、Manipulation、Gripper、Perception、SimulationGrasp、Interlock、Evidence。

Project integration packages：combined description、combined MoveIt config、opt-in bringup、exact dependency manifest。

当前没有任何已知requirement需要patch upstream core。若未来出现gap，先提交ADR说明：requirement、upstream behavior、adapter为何不足、最小patch、pin、tests、rebase/update plan。

## 12. Gate 1 upstream stop conditions

以下任一成立即停止，不进入combined runtime：

- U1 UR control或U2 MoveIt standalone baseline未通过；
- exact dependency snapshot未冻结；
- two Gazebo/two `/clock`/two controller managers或duplicate TF authority；
- combined MoveIt仍只看到arm-only model或漏掉base/mount/gripper collision；
- gripper/controller resource owner不唯一；
- simulation grasp仍是假设却被报告为VERIFIED。
