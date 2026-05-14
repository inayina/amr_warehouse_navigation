# AMR Warehouse Simulation Resume Bullets

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


## 最近（2026-05）

- 合并 Mock WMS 到 `amr_warehouse_sim`，并将 legacy `scripts/` 转为兼容 shim。
- 实现 HTTP Mock WMS executor 与 FastAPI API（任务创建/查询/状态回写）。
- 编写集成契约测试覆盖 executor、runner 与 HTTP API，本地验证通过（63 passed）。
- 添加 GitHub Actions CI：在 push/PR 上运行 `make test`；补充 CI 测试说明文档。
- 整理 WMS 文档并记录短期扩展计划，保持 Nav2 V2 基线稳定。

## Recent (2026-05)

- Consolidated Mock WMS into `amr_warehouse_sim` and converted legacy `scripts/` into compatibility shims.
- Implemented an HTTP Mock WMS executor and a FastAPI `mock_wms_api` for task create/list/patch.
- Added integration and contract tests for executor, runner, and HTTP API (63 tests passed locally).
- Added GitHub Actions CI to run `make test` on push/PR and a CI test-summary document.
- Consolidated WMS docs and captured short-term extension notes while keeping the Nav2 V2 baseline stable.
