# Gate 0 preflight and upstream reproduction

日期：`2026-08-28`  
状态：**VERIFIED（scope: existing AMR control group + upstream U1/U2/U3）**

本报告不代表 Gate 1+ 的 combined model、Nav2、grasp、place 或任务链通过。

| Item | Evidence |
| --- | --- |
| Checkout | `feature/mobile-manipulation-mvp@c8af1cfe992591a572f5e2f51833b76e64f4437f` |
| Python regression | `187 passed` (`.venv/bin/python -m pytest test -q -p no:cacheprovider`) |
| Existing AMR runtime | current `navigation.launch.py` headless；Nav2 lifecycle active，`candidate_dock_a` temporary-db task `SUCCEEDED` |
| Protected AMR baseline | no edit to navigation/slam launch、Nav2 params、maps、current model/world、Mock WMS/Fleet/inspection runtime |

## Frozen installed dependency set

| Package | Installed version |
| --- | --- |
| `ur_description` | `3.5.1-1noble.20260615.175716` |
| `ur_simulation_gz` | `2.5.0-1noble.20260617.155357` |
| `ur_robot_driver` | `3.8.0-1noble.20260615.175905` |
| `gz_ros2_control` | `1.2.19-1noble.20260615.171757` |
| `gz_ros2_control_demos` | `1.2.19-1noble.20260616.073637` |

首次 U1 使用旧 `gz_ros2_control 1.2.17` 在 controller-manager 初始化后 exit 139。升级到上表 `1.2.19` 后成功，故它是 Gate 1 的 working freeze。

## U1 — official UR control: VERIFIED

`ur_sim_control.launch.py` 中 `joint_state_broadcaster`、`scaled_joint_trajectory_controller` 都为 `active`。3 s 小幅 six-joint goal 返回 `SUCCEEDED`，最终状态到达 `[0.10, -1.47, 0.10, -1.47, 0.10, 0.10]`。

## U2 — official UR + MoveIt: VERIFIED

`ur_sim_moveit.launch.py` 启动 `move_group`、规划与 controller mapping。`/plan_kinematic_path` 对 `ur_manipulator` 返回 `MoveItErrorCodes.val=1`（约 19 ms）。带当前状态首点的 `/execute_trajectory` 返回 `val=1 / SUCCEEDED`，日志确认 MoveIt dispatch 到 `scaled_joint_trajectory_controller` 并收到 controller terminal success。

## U3 — official mimic gripper: VERIFIED

`gripper_mimic_joint_example_position.launch.py` 中两个 controller 为 `active`。向 `/gripper_controller/commands` 发布 `[0.10]` 后，左右 finger feedback 均从 `0.15` 到约 `0.10`。DART 的 mimic-constraint 警告不外推为接触、夹持或物理抓取成功。

## Gate decision

Gate 0 **PASS**。允许 Gate 1 opt-in description/control implementation；combined-model failure 不回写为 AMR mainline regression。
