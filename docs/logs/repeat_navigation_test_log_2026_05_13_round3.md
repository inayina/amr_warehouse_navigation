# 2026-05-13 Repeat Navigation Supplement Log Round 3

## Scope

- 目的：在不改主线配置的前提下，自选并补完剩余有坐标的历史候选点尝试
- 本轮点位：`staging_1`、`inspection_point`
- 不改文件：`launch/navigation.launch.py`、`config/nav2_params.yaml`、地图、world、robot model
- 本轮结果：两个点都完成了独立 fresh session 复测，但都因前置条件不足被如实记为 `SKIPPED`

## Commands

### `staging_1`

```bash
ros2 daemon stop
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30
ros2 daemon start
ros2 node list
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
timeout 4s ros2 run tf2_ros tf2_echo map odom
ros2 action info /navigate_to_pose
ros2 action list -t
```

### `inspection_point`

```bash
ros2 daemon stop
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30
ros2 node list
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
timeout 4s ros2 run tf2_ros tf2_echo map odom
ros2 action info /navigate_to_pose
ros2 action list -t
```

## Key Outputs

### `staging_1`

```text
initial pose:
[INFO] [initial_pose_publisher]: Found 1 subscriber(s) on /initialpose.
[INFO] [initial_pose_publisher]: Published initial pose 1/10 ... 10/10

ros2 node list:
/amcl
/behavior_server
/bt_navigator
/controller_server
/docking_server
/lifecycle_manager_localization
/lifecycle_manager_navigation
/map_server
/planner_server
/route_server
/velocity_smoother
/waypoint_follower
...

ros2 lifecycle get /map_server -> active [3]
ros2 lifecycle get /controller_server -> active [3]
ros2 lifecycle get /bt_navigator -> active [3]
ros2 lifecycle get /amcl -> Node not found
ros2 lifecycle get /planner_server -> Node not found

tf2_echo map odom:
- Translation: [0.004, 0.023, 0.000]
- Rotation: in RPY (degree) [0.000, -0.000, 0.327]

ros2 action info /navigate_to_pose:
Action: /navigate_to_pose
Action clients: 1
    /docking_server
Action servers: 0

ros2 action list -t:
/navigate_to_pose [nav2_msgs/action/NavigateToPose]
...
```

结论：

- `staging_1` 独立 fresh session 已完成
- `map -> odom` 可用
- lifecycle 未形成完整 `5/5 active`
- `/navigate_to_pose` 没有可用 server
- 按约束 `SKIPPED`，未发 goal

### `inspection_point`

```text
initial pose:
[INFO] [initial_pose_publisher]: Found 1 subscriber(s) on /initialpose.
[INFO] [initial_pose_publisher]: Published initial pose 1/10 ... 10/10

ros2 node list:
/amcl
/behavior_server
/bt_navigator
/controller_server
/docking_server
/lifecycle_manager_localization
/lifecycle_manager_navigation
/map_server
/planner_server
/route_server
/velocity_smoother
/waypoint_follower
...

ros2 lifecycle get /map_server -> active [3]
ros2 lifecycle get /planner_server -> active [3]
ros2 lifecycle get /controller_server -> active [3]
ros2 lifecycle get /amcl -> active [3]  (retry)
ros2 lifecycle get /bt_navigator -> Node not found
ros2 lifecycle get /bt_navigator -> Node not found  (retry)

tf2_echo map odom:
- Translation: [0.005, 0.026, 0.000]
- Rotation: in RPY (degree) [0.000, -0.000, 0.475]

ros2 action info /navigate_to_pose:
Action: /navigate_to_pose
Action clients: 3
    /bt_navigator
    /waypoint_follower
    /docking_server
Action servers: 1
    /bt_navigator
```

结论：

- `inspection_point` 独立 fresh session 已完成
- `map -> odom` 可用
- `/navigate_to_pose` 有可用 server
- 但 lifecycle 仍未形成完整 `5/5 active`，因为 `bt_navigator` 连续两次返回 `Node not found`
- 按约束 `SKIPPED`，未发 goal

## Round Summary

- 成功点：`无`
- 失败点：`无`
- 跳过点：`staging_1`、`inspection_point`
- 剩余未测点：`station_a`、`station_b`、`shelf_1`、`shelf_2`
- 备注：历史候选点已经全部完成独立尝试；其中 `candidate_dock_a`、`buffer_1` 成功，`staging_1`、`inspection_point` 因前置条件不足被真实跳过
