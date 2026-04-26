# AMR Warehouse Simulation Resume Bullets

这份文档用于整理当前项目可直接复用的中英文简历要点，内容尽量贴合仓库当前真实状态，适合后续按校招、实习、社招或项目介绍场景二次裁剪。

## 中文版

- 基于 ROS 2 Jazzy 与 Gazebo Harmonic 搭建 AMR 仓库仿真项目，完成从仿真场景、差速机器人模型、激光雷达到 `/cmd_vel`、`/odom`、`/scan`、TF 的基础链路集成。
- 使用 `laser_filters`、`slam_toolbox` 和自定义 `odom_tf_node` 打通 SLAM 建图最小闭环，实现 `/scan` 到 `/scan_filtered`、`/map` 输出以及地图保存流程。
- 围绕 Nav2 搭建导航主线，完成 `map_server`、AMCL、planner、controller、RViz 的参数组织与启动集成，建立 `map -> odom -> base_link` 导航链路。
- 基于仓库货架场景对 footprint、inflation、progress checker、MPPI controller 和 A* 全局规划参数进行收敛，形成可复现的短距离导航稳定基线。
- 为项目补充 `pytest` 基础测试目录，覆盖地图入口校验、Nav2 关键参数回归和 launch smoke test，建立更接近工程实践的验证入口。

## English Version

- Built an AMR warehouse simulation project on ROS 2 Jazzy and Gazebo Harmonic, integrating the warehouse world, differential-drive robot model, LiDAR, and the core `/cmd_vel`, `/odom`, `/scan`, and TF data flow.
- Implemented a minimum SLAM mapping loop with `laser_filters`, `slam_toolbox`, and a custom `odom_tf_node`, enabling the `/scan` to `/scan_filtered` pipeline, `/map` generation, and map persistence.
- Set up the Nav2 navigation stack by organizing launch and parameter files for `map_server`, AMCL, planner, controller, and RViz, and established the `map -> odom -> base_link` localization and navigation chain.
- Tuned navigation behavior for a warehouse aisle environment by refining footprint, inflation, progress checker, MPPI controller, and A* global planning parameters to create a repeatable short-range navigation baseline.
- Added a foundational `pytest` test structure covering map asset validation, Nav2 configuration regression checks, and launch smoke tests to make the project workflow closer to real engineering practice.

## 使用建议

- 中文简历优先保留 3 到 4 条，突出 ROS 2、Gazebo、SLAM、Nav2 和测试方法。
- 英文简历可优先使用动词开头版本，例如 Built、Implemented、Set up、Tuned、Added。
- 如果后续补了 `launch_testing`、bag 回放回归或真机测试，可以继续在这里追加更偏测试工程的 bullet points。
