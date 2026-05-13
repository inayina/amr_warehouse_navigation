# 2026-05-13 Repeat Navigation Supplement Log

## Scope

- 目的：基于 `docs/reports/repeat_navigation_test_report_2026_05_13.md` 继续补测尚未验证的导航点
- 约束：不修改 `navigation.launch.py`、`config/nav2_params.yaml`、地图、world、robot model
- 本轮实际变更：只补测试报告和本日志

## Point Scan

- 已测点（补测开始前）：`candidate_dock_a`；`start_zone` 已作为 `/initialpose` 入口多次验证
- 未测点（补测开始前）：`station_a`、`station_b`、`shelf_1`、`shelf_2`
- 历史候选可补测点：`buffer_1`、`staging_1`、`inspection_point`

## Commands

```bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
timeout 4s ros2 run tf2_ros tf2_echo map odom
timeout 4s ros2 run tf2_ros tf2_echo odom base_link
ros2 action info /navigate_to_pose
timeout 20s ros2 topic echo /cmd_vel --once
timeout 120s ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: 2.4, y: -3.8, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}"
ros2 action list -t
ros2 node list
```

## Key Outputs

### Initial Pose Injection

```text
[INFO] [initial_pose_publisher]: Found 1 subscriber(s) on /initialpose.
[INFO] [initial_pose_publisher]: Published initial pose 1/10: x=0.000, y=0.000, yaw=0.000 rad, frame=map
...
[INFO] [initial_pose_publisher]: Published initial pose 10/10: x=0.000, y=0.000, yaw=0.000 rad, frame=map
```

### Lifecycle / TF / Action Before `buffer_1`

```text
ros2 lifecycle get /map_server -> active [3]
ros2 lifecycle get /amcl -> active [3]
ros2 lifecycle get /planner_server -> active [3]
ros2 lifecycle get /controller_server -> active [3]
ros2 lifecycle get /bt_navigator -> active [3]

tf2_echo map odom:
- Translation: [0.012, 0.023, 0.000]
- Rotation: in RPY (degree) [0.000, -0.000, 0.095]

tf2_echo odom base_link:
- Translation: [-0.000, -0.000, 0.000]
- Rotation: in RPY (degree) [0.000, -0.000, 0.000]

ros2 action info /navigate_to_pose:
Action: /navigate_to_pose
Action clients: 3
    /bt_navigator
    /waypoint_follower
    /docking_server
Action servers: 1
    /bt_navigator
```

### `buffer_1` Goal

```text
/cmd_vel first message:
linear:
  x: 0.01997709833085537
angular:
  z: -0.518447995185852

ros2 action send_goal /navigate_to_pose ... buffer_1:
Goal accepted with ID: a8f66440b9d943e98884647f1fe81dfa

Result:
    error_code: 0
error_msg: ''

Goal finished with status: SUCCEEDED
```

### Post-Goal Recheck That Stopped Further Goals

```text
ros2 lifecycle get /planner_server -> active [3]
ros2 lifecycle get /bt_navigator -> Node not found

tf2_echo map odom:
- Translation: [0.091, 0.081, 0.000]
- Rotation: in RPY (degree) [0.000, 0.000, -1.213]

ros2 action info /navigate_to_pose:
Action: /navigate_to_pose
Action clients: 0
Action servers: 0

ros2 action list -t:
/backup [nav2_msgs/action/BackUp]
/compute_and_track_route [nav2_msgs/action/ComputeAndTrackRoute]
/compute_path_through_poses [nav2_msgs/action/ComputePathThroughPoses]
/compute_path_to_pose [nav2_msgs/action/ComputePathToPose]
/compute_route [nav2_msgs/action/ComputeRoute]
/follow_path [nav2_msgs/action/FollowPath]
/navigate_to_pose [nav2_msgs/action/NavigateToPose]
/smooth_path [nav2_msgs/action/SmoothPath]
/spin [nav2_msgs/action/Spin]
/wait [nav2_msgs/action/Wait]

ros2 node list:
/amcl
/docking_server
/lifecycle_manager_localization
/odom_tf_publisher
/robot_state_publisher
/robot_state_publisher
/ros_gz_bridge
/scan_to_scan_filter_chain
/static_transform_publisher_SYpCJBXlk92Ad93p
/static_transform_publisher_exwLIDUUy1wtAXZx
/velocity_smoother
```

## Result Summary

- 成功点：`buffer_1`
- 失败点：`无`
- 跳过点：`station_a`、`station_b`、`shelf_1`、`shelf_2`、`staging_1`、`inspection_point`
- 停止原因：主线四点缺坐标；`RUN-06` 后 lifecycle / action 复核不一致，不满足继续强发 goal 的条件
