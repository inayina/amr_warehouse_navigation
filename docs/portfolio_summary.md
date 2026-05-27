# Portfolio Summary

日期：`2026-05-27`

## 1. One Sentence

AMR 仿真导航子系统：基于 ROS 2 Jazzy、Gazebo Harmonic、SLAM Toolbox、Nav2 和 SQLite / FastAPI Mock WMS，构建可复现的仓储 AMR 建图、定位、导航与任务执行数据链，并作为 Robot Ops Dashboard 的仿真任务数据来源。

## 2. Project Positioning

本仓库不是完整 WMS 或多机器人调度平台，而是机器人运维展示系统中的 AMR 仿真导航子系统。它负责生成和验证以下数据：

- 仓库仿真环境与机器人运动状态
- SLAM 建图结果与 Nav2 可用地图
- AMCL 定位与 TF 状态
- 固定任务点 NavigateToPose 执行结果
- Mock WMS 任务创建、查询、执行和状态回写
- Dashboard 可读取的最小 HTTP task 数据

## 3. What Was Built

- 搭建 Gazebo 仓库世界、差速 AMR、雷达、里程计和 ROS-Gazebo bridge。
- 打通 `/scan -> /scan_filtered -> slam_toolbox -> maps/warehouse.yaml` 建图链路。
- 建立 `map_server -> AMCL -> planner/controller/bt_navigator -> /cmd_vel` 的 Nav2 稳定导航基线。
- 固定 `start_zone`、`station_a`、`station_b`、`shelf_1`、`shelf_2` 等 map frame 任务点。
- 实现 SQLite Mock WMS CLI、FastAPI HTTP API、executor 和 task runner。
- 用 ready gate 保护任务执行，避免 Nav2 lifecycle / action 未就绪时盲目发送 goal。
- 整理测试、验收清单、验证报告和可视化录屏指南。

## 4. Technical Highlights

- ROS 2 lifecycle 与 Nav2 action readiness 检查被纳入任务执行前置条件。
- initial pose 通过脚本化 preset 固定，降低手工 RViz 点击带来的复现差异。
- Mock WMS 与 Nav2 保持清晰边界：数据层负责 task，executor 负责 action 调用，Nav2 负责导航，Dashboard 只读取或代理任务 API。
- 文档明确区分已完成能力、软件骨架、后续规划和不应宣称的边界。
- 自动化测试覆盖地图 / YAML / CLI / HTTP API / executor contract / task runner contract 等非 GUI 可回归部分。

## 5. Demo Story

推荐展示路径：

1. 启动 `navigation.launch.py`，展示 Gazebo 仓库环境与 RViz 地图。
2. 发布 `start_zone` initial pose，展示 `map -> odom -> base_link` 和 AMCL 定位。
3. 通过 CLI 或 HTTP API 创建 `station_a` / `station_b` 任务。
4. 执行 `mock_wms_task_runner --execute`，展示 NavigateToPose goal、机器人运动和任务状态回写。
5. 在 Robot Ops Dashboard 中展示任务列表、任务状态和 AMR 仿真任务数据来源。

## 6. Resume Bullets

- Built a ROS 2 Jazzy AMR simulation navigation subsystem with Gazebo, SLAM Toolbox, Nav2, AMCL, RViz, and fixed warehouse task points.
- Implemented a minimal Mock WMS task pipeline using SQLite, CLI tools, FastAPI, and a Nav2 NavigateToPose executor with readiness checks.
- Established a reproducible navigation baseline with saved SLAM map, scripted initial pose publishing, lifecycle validation, and task execution reports.
- Integrated the AMR simulation task data boundary with a Robot Ops Dashboard through a minimal HTTP task API.

## 7. Current Boundaries

- The system drives a simulated AMR in Gazebo, not a real motor controller.
- The Mock WMS is a minimal task source, not a production warehouse management system.
- The Dashboard consumes task and status data but does not own Nav2 scheduling or `/cmd_vel` control.
- Multi-robot coordination, order management, storage allocation and production deployment are outside the current mainline.

## 8. Suggested Visual Assets

See [../artifacts/screenshots/README.md](../artifacts/screenshots/README.md) for the screenshot checklist.
