# Docs Index

本文件用于整理 `docs/` 目录的阅读入口，避免把“当前主线文档”“设计说明”“操作指南”“阶段测试报告”“诊断日志”和“模板”混在一起看。

## 1. 推荐阅读顺序

如果你现在要判断项目主线状态，建议按下面顺序读：

1. [design.md](./design.md)
   当前主线设计、阶段状态、稳定入口和边界说明。
2. [prd_mock_wms_task_flow.md](./prd_mock_wms_task_flow.md)
   面向项目经理 / 技术产品 / 系统集成岗位的最小功能说明。
3. [system_architecture.md](./system_architecture.md)
   任务链路和验证链路的系统结构图。
4. [acceptance_checklist.md](./acceptance_checklist.md)
   面向验收的检查表、命令入口和证据追溯。
5. [roadmap.md](./roadmap.md)
   近中期路线图，说明当前优先级和下一阶段目标。
6. [troubleshooting.md](./troubleshooting.md)
   V1 / V2 排障顺序和常用检查命令。
7. [fixed_task_points.md](./fixed_task_points.md)
   当前主线固定任务点入口与点位状态。
8. [designs/README.md](./designs/README.md)
   WMS 相关设计、计划与演进文档入口。
9. [container_usage.md](./container_usage.md)
   当前 Docker / devcontainer 轻量开发入口、支持范围与边界说明。
10. [guides/README.md](./guides/README.md)
   WMS 相关手动测试、CLI 说明与操作指南入口。
11. [reports/README.md](./reports/README.md)
   正式验证结果入口。
12. [logs/README.md](./logs/README.md)
   过程日志与诊断记录入口。
13. [templates/README.md](./templates/README.md)
   报告模板入口。

## 2. 当前主线入口文档

这些文件属于“当前状态说明”，优先维护，优先引用：

- [design.md](./design.md)
  当前稳定基线、主线文件、阶段说明。
- [prd_mock_wms_task_flow.md](./prd_mock_wms_task_flow.md)
  当前最小任务闭环的 PRD / 功能说明。
- [system_architecture.md](./system_architecture.md)
  当前任务链路与验证链路结构图。
- [acceptance_checklist.md](./acceptance_checklist.md)
  当前验收项、验证方法和证据入口。
- [roadmap.md](./roadmap.md)
  当前公开路线图。
- [troubleshooting.md](./troubleshooting.md)
  主线排障入口。
- [fixed_task_points.md](./fixed_task_points.md)
  `config/task_points.yaml` 的主线解释。
- [future_architecture.md](./future_architecture.md)
  未来扩展边界，不等同于“已经实现”。
- [container_usage.md](./container_usage.md)
  当前 Docker / devcontainer 入口与本机边界说明。

## 3. WMS 设计与计划

这些文件主要描述 WMS 当前边界、设计决策和后续演进方向：

- [designs/README.md](./designs/README.md)
  设计子目录索引。
- [designs/mock_wms_design.md](./designs/mock_wms_design.md)
  最小 Mock WMS 数据层、executor、HTTP API 和 live 验证的总边界。
- [designs/mock_wms_executor_design.md](./designs/mock_wms_executor_design.md)
  单条 executor 的 ready gate、状态机与 execute 边界。
- [designs/mock_wms_executor_http_design.md](./designs/mock_wms_executor_http_design.md)
  executor 从 SQLite 演进到 HTTP 取任务的边界设计。
- [designs/mock_wms_http_api_plan.md](./designs/mock_wms_http_api_plan.md)
  最小 Mock WMS HTTP API 的范围与收口计划。

## 4. 使用与测试指南

这些文件更偏操作说明、手工验证和入口解释：

- [guides/README.md](./guides/README.md)
  指南子目录索引。
- [container_usage.md](./container_usage.md)
  当前主线的 Docker / devcontainer 轻量开发入口说明。
- [guides/mock_wms_visual_demo_recording_guide.md](./guides/mock_wms_visual_demo_recording_guide.md)
  可视化演示、录屏和 GitHub 展示说明。
- [guides/mock_wms_http_api_manual_test_guide.md](./guides/mock_wms_http_api_manual_test_guide.md)
  最小 Mock WMS HTTP API 的逐步手动测试指南。
- [guides/mock_wms_cli_entrypoints_explained.md](./guides/mock_wms_cli_entrypoints_explained.md)
  Mock WMS CLI / executor / task runner 入口桥接说明。

## 5. 阶段测试报告

这些文件记录“某一天真实执行过什么、结果如何”，保留事实，不回写改数：

- [reports/README.md](./reports/README.md)
  报告子目录索引。
- [reports/test_report_2026_05_12.md](./reports/test_report_2026_05_12.md)
  V2.1 baseline test report。
- [reports/repeat_navigation_test_report_2026_05_13.md](./reports/repeat_navigation_test_report_2026_05_13.md)
  V2.2 固定任务点与重复导航测试报告。
- [reports/v2_validation_closure_2026_05_13.md](./reports/v2_validation_closure_2026_05_13.md)
  V2.1 / V2.2 收口记录。
- [wms/reports/wms_task_points_readiness_report_2026_05_13.md](./wms/reports/wms_task_points_readiness_report_2026_05_13.md)
  WMS readiness 复测报告。
- [wms/reports/mock_wms_executor_execute_validation_2026_05_13.md](./wms/reports/mock_wms_executor_execute_validation_2026_05_13.md)
  Mock WMS executor execute-mode 验证。
- [wms/reports/mock_wms_task_runner_live_validation_2026_05_13.md](./wms/reports/mock_wms_task_runner_live_validation_2026_05_13.md)
  Mock WMS task runner live 验证。
- [wms/reports/mock_wms_http_api_validation_2026_05_14.md](./wms/reports/mock_wms_http_api_validation_2026_05_14.md)
  Mock WMS HTTP API 验证。
- [reports/collision_monitor_stage1_test_report.md](./reports/collision_monitor_stage1_test_report.md)
  `collision_monitor` stage1 实验记录。

## 6. 诊断日志

- [logs/README.md](./logs/README.md)
  日志子目录索引。
- [logs/nav2_startup_stability_notes.md](./logs/nav2_startup_stability_notes.md)
  fresh-session 下 Nav2 启动前置条件不稳定现象总结。
- [logs/nav2_startup_stability_log_2026_05_13.md](./logs/nav2_startup_stability_log_2026_05_13.md)
  启动稳定性诊断日志。
- [logs/repeat_navigation_test_log_2026_05_13_round2.md](./logs/repeat_navigation_test_log_2026_05_13_round2.md)
  重复导航补测日志。
- [logs/repeat_navigation_test_log_2026_05_13_round3.md](./logs/repeat_navigation_test_log_2026_05_13_round3.md)
  重复导航补测日志。

## 7. 模板与辅助说明

这些文件主要服务于后续继续记录和整理，不直接代表当前主线状态：

- [templates/README.md](./templates/README.md)
  模板子目录索引。
- [templates/test-report-template.md](./templates/test-report-template.md)
  通用机器人测试报告模板。
- [templates/repeat_navigation_test_report.md](./templates/repeat_navigation_test_report.md)
  V2.2 重复导航模板。
- [task_points_coordinate_plan.md](./task_points_coordinate_plan.md)
  任务点候选坐标规划说明。
- [resume-bullets.md](./resume-bullets.md)
  对外展示 / 简历素材。
- [interview_talking_points.md](./interview_talking_points.md)
  面试讲项目时可直接复用的结构化提纲。

## 8. 当前 WMS 主线判断

截至 `2026-05-14`，当前更准确的结论是：

- 可以接回主线的部分：
  最小 Mock WMS 数据层、最小 HTTP create/query API，以及受 ready gate 保护的最小 executor / 顺序 runner。
- 不建议现在接回主线的部分：
  旧 `future_extensions/wms_integration` 的执行链路、更完整调度 / MQTT / 多机器人逻辑，以及常驻 task service。

原因很直接：

- 当前 `station_a`、`station_b`、`shelf_1`、`shelf_2` 已有真实 `SUCCEEDED` 证据，足以支撑数据层 intake 和最小 executor 入口。
- 但 fresh-session 下 lifecycle / action readiness 仍存在波动，`shelf_1`、`shelf_2` 也出现过有效前置条件下的 `ABORTED`。
- 因此，现在适合把 WMS 表述为“主线可引用的最小任务链路能力”，不适合把完整任务执行链路或调度系统宣称为当前主线能力。

## 9. 当前整理策略

这次整理已经完成主目录物理分层：

- `docs/reports/`
  放正式测试报告和结果文档。
- `docs/logs/`
  放诊断说明、补测日志和过程记录。
- `docs/templates/`
  放可复用的报告模板和记录骨架。
- `docs/designs/`
  放 WMS 相关设计、计划和边界文档。
- `docs/guides/`
  放 WMS 相关操作说明、手测指南和入口解释。

当前仍保留在 `docs/` 顶层的，是主线设计、排障、路线图和少量全局辅助说明文档。

这样做的原因是：

- 当前很多文档之间已经互相链接；
- 当前需要优先把“当前主线”“设计说明”“操作指南”“正式结果”“过程日志”拆开；
- 同时又不希望把主线入口文档埋进过深目录。
