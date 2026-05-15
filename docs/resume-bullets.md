# Resume Bullets

日期：`2026-05-14`

## 1. 项目一句话定位

中文版：

将 ROS 2 Nav2 仿真项目收口为一个“物流机器人任务执行与导航验证系统”最小闭环案例，打通了固定任务点、SQLite Mock WMS、任务执行器、Nav2 导航和测试验收文档。

English:

Wrapped a ROS 2 Nav2 simulation into a minimal "warehouse robot task execution and navigation validation" case, connecting fixed task points, a SQLite-backed Mock WMS, task execution, Nav2 navigation, and acceptance-oriented documentation.

## 2. 简历版摘要：中文版短版

适合放在项目经历里，控制在 `3` 条左右：

- 基于 ROS 2 Jazzy、Gazebo Harmonic 和 Nav2 搭建仓储 AMR 仿真项目，形成 `navigation.launch.py + nav2_params.yaml + warehouse.yaml` 的稳定导航基线。
- 设计并落地最小 Mock WMS 任务闭环，使用 `config/task_points.yaml`、SQLite、CLI、HTTP API、executor 和 task runner 打通“任务创建 -> 查询 -> 执行 -> 状态回写”链路。
- 建立自动化测试、运行时验证报告和验收清单，形成面向物流机器人任务执行、导航验证和系统集成展示的项目案例。

## 3. 简历版摘要：中文版展开版

适合放在较完整的项目描述中，控制在 `4~6` 条：

- 基于 ROS 2 Jazzy 与 Gazebo Harmonic 构建 AMR 仓储仿真环境，完成机器人模型、`/cmd_vel`、`/odom`、`/scan`、TF 与可视化链路集成。
- 使用 `laser_filters`、`slam_toolbox` 和自定义 `odom_tf_node` 打通建图闭环，并固化 `maps/warehouse.yaml` 作为 Nav2 地图入口。
- 围绕仓储货架场景收敛 Nav2 参数，建立 AMCL、planner、controller、`bt_navigator` 的稳定启动与短距离导航基线。
- 在不改导航主线的前提下，引入 SQLite Mock WMS、任务创建 / 查询 CLI、最小 HTTP API、单条 executor 与顺序 task runner，形成最小任务执行闭环。
- 为固定任务点、Mock WMS 数据层、executor / task runner、HTTP API 和导航配置补齐自动化测试与运行时验证文档，本地 `make test` 最新结果为 `63 passed`。
- 输出 PRD、系统架构图、验收清单、测试报告和录屏指南，把项目包装为可用于简历、面试和 GitHub 展示的物流机器人案例。

## 4. 简历版摘要：English

Short version:

- Built a warehouse AMR simulation project on ROS 2 Jazzy, Gazebo Harmonic, and Nav2, and stabilized the navigation baseline around `navigation.launch.py`, `nav2_params.yaml`, and `warehouse.yaml`.
- Added a minimal Mock WMS task flow using fixed task points, SQLite, CLI tools, a lightweight HTTP API, an executor, and a sequential task runner to cover task creation, query, execution, and status writeback.
- Added automated tests, runtime validation reports, and acceptance-oriented documentation so the project can be presented as a warehouse robot task execution and navigation validation case.

Expanded version:

- Integrated the warehouse simulation world, robot model, LiDAR, `/cmd_vel`, `/odom`, `/scan`, TF, and RViz visualization into a working AMR simulation pipeline.
- Implemented the mapping baseline with `laser_filters`, `slam_toolbox`, and a custom `odom_tf_node`, then standardized `maps/warehouse.yaml` as the Nav2 map entry.
- Stabilized the Nav2 stack for the warehouse scenario by organizing AMCL, planner, controller, and `bt_navigator` into a repeatable navigation baseline.
- Extended the project with a minimal SQLite-backed Mock WMS flow, including CLI task intake, HTTP task create/query/status APIs, a single-task executor, and a sequential task runner.
- Added regression and contract coverage for configuration, task points, Mock WMS, executor, task runner, and HTTP API, with the latest local `make test` result at `63 passed`.
- Packaged the project with PRD, architecture, acceptance, validation, and demo-recording docs for resume, interview, and GitHub portfolio usage.

## 5. 按岗位侧重点取舍

### 项目经理 / 技术产品经理

- 强调“最小闭环”而不是“技术堆栈很多”。
- 关键词优先用：任务创建、任务执行、导航验证、状态回写、验收清单、文档追溯。
- 少讲底层参数调优细节，多讲边界控制、阶段推进、验收口径和项目包装能力。

可直接摘用：

- 把一个 ROS 2 导航仿真项目收口为“物流机器人任务执行与导航验证系统”最小案例，明确了任务闭环、系统边界和验收口径。
- 通过 PRD、架构图、验收清单和测试报告，把技术实现整理成更适合面试和 GitHub 展示的项目叙事。

### 机器人系统集成岗位

- 强调“任务层如何安全接回导航层”。
- 关键词优先用：ready gate、fixed task points、NavigateToPose、lifecycle checks、status writeback、运行时验证。
- 可以保留“只在 Nav2 ready 后发送 goal、不直接控制 `/cmd_vel`”这类边界表达。

可直接摘用：

- 在不改 Nav2 稳定基线的前提下，用 fixed task points、SQLite Mock WMS、executor 和 task runner 验证了上层任务入口与导航执行链的最小集成方式。
- 通过 lifecycle、TF 和 `/navigate_to_pose` ready checks 约束任务执行时机，避免系统未 ready 时盲目下发导航目标。

## 6. 建议避免的表述

- 不要写成“完整 WMS 系统”
- 不要写成“多机器人调度平台”
- 不要写成“生产级后端系统”
- 不要把运行时 `ready gate` 波动说成已经完全解决

更稳妥的表达方式：

- 最小 Mock WMS 任务闭环
- 面向物流机器人任务执行与导航验证的项目案例
- 适合演示、验证和系统集成说明，不宣称生产落地
