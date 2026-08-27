# Gate 1 opt-in description and control

状态：**VERIFIED（scope: isolated Gazebo component bringup）**

## Delivered scope

- 新增 `mobile_manipulation/amr_mm_description` 与 `mobile_manipulation/amr_mm_bringup`，仅通过 explicit-colcon base path 构建，不改变 default AMR package graph。
- 组合 xacro 使用 official UR5e macro（`arm_` prefix），以 `arm_flange` 挂载双指夹爪、`mm_tcp` 和 camera；不虚构 `flange -> tool0` edge。
- native Gazebo DiffDrive 保留 wheel ownership；`MMArmGripperSystem` 只声明六个 `arm_*` joint 与 `mm_left_finger_joint`。
- 独立 headless launch 启动一个 Gazebo、一个 `/clock` bridge、一个 RSP 和一个 controller manager；不 include existing AMR launch。

## Evidence

| Check | Observed result |
| --- | --- |
| Build | two packages finished under isolated `build/install/log mm_gate1` |
| Xacro | composite model expanded with `arm_flange`, `arm_tool0`, `mm_tcp`, wheels and `MMArmGripperSystem` |
| Ownership | active joint-state/arm/gripper controllers; only 6 arm + 1 gripper command interfaces; no wheel interface |
| Arm action | 3 s goal `SUCCEEDED`; six joints reached ±`0.02` rad |
| Gripper action | position `0.02` returned `SUCCEEDED`; feedback `0.02` |
| TF | `/tf` has one publisher (`robot_state_publisher`); `base_link -> mm_tcp` resolved |

## Boundaries and residual risks

- `position_controllers/GripperActionController` is deprecated on this host; its replacement package is absent. This stays an explicit Gate 3/upgrade decision.
- DART reports no native mimic constraint; controller-visible driver state is proven, not contact/grasp physics.
- Empty-world component evidence does not prove `/cmd_vel`/`/odom` Nav2 bridging, base stability, MoveIt for the combined model, collision quality, perception, Mission, grasp/place, or hardware.
