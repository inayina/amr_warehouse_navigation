# Screenshots Artifacts

日期：`2026-05-27`

本目录用于存放当前 AMR 仿真导航子系统的作品集 / README 截图素材。建议只放当前主线截图，不放历史 GIF 或已经偏离当前 launch / config 的素材。

## Recommended Screenshots

| 建议文件名 | 内容 | 目的 |
| --- | --- | --- |
| `gazebo_warehouse_environment.png` | Gazebo 仓库环境和 `my_robot` | 展示仿真场景、机器人模型和仓库语境 |
| `slam_mapping_result.png` | SLAM 建图结果或 RViz map 视图 | 展示 `/scan_filtered -> slam_toolbox -> map` 建图成果 |
| `nav2_goal_navigation.png` | RViz 中 Nav2 Goal、global path、local costmap 与 Gazebo 机器人运动 | 展示固定目标点导航执行 |
| `rviz_tf_topic_status.png` | RViz TF / topic 状态，或终端 lifecycle + action readiness 检查 | 展示 `map -> odom -> base_link`、Nav2 lifecycle 和 `/navigate_to_pose` ready 状态 |

## Capture Notes

- 优先使用当前主线：`launch/navigation.launch.py`、`config/nav2_params.yaml`、`maps/warehouse.yaml`、`config/task_points.yaml`。
- 截图前先发布 initial pose：`ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`。
- Nav2 导航截图建议选择 `station_a` 或 `station_b`，避免使用未验证的新点位。
- 如果截图用于 README 或作品集，文件名保持稳定，方便后续链接。
