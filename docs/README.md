# Docs Index

本文件用于整理 `docs/` 目录的阅读入口，避免把“当前主线文档”“阶段测试报告”“诊断日志”和“模板”混在一起看。

## 1. 推荐阅读顺序

如果你现在要判断项目主线状态，建议按下面顺序读：

1. [design.md](./design.md)
   当前主线设计、阶段状态、稳定入口和边界说明。
2. [roadmap.md](./roadmap.md)
   近中期路线图，说明当前优先级和下一阶段目标。
3. [troubleshooting.md](./troubleshooting.md)
   V1 / V2 排障顺序和常用检查命令。
4. [fixed_task_points.md](./fixed_task_points.md)
   当前主线固定任务点入口与点位状态。
5. [mock_wms_design.md](./mock_wms_design.md)
   最小 Mock WMS 数据层的边界与当前主线判断。

## 2. 当前主线文档

这些文件属于“当前状态说明”，优先维护，优先引用：

- [design.md](./design.md)
  当前稳定基线、主线文件、阶段说明。
- [roadmap.md](./roadmap.md)
  当前公开路线图。
- [troubleshooting.md](./troubleshooting.md)
  主线排障入口。
- [fixed_task_points.md](./fixed_task_points.md)
  `config/task_points.yaml` 的主线解释。
- [mock_wms_design.md](./mock_wms_design.md)
  最小 Mock WMS 数据层设计。
- [future_architecture.md](./future_architecture.md)
  未来扩展边界，不等同于“已经实现”。

## 3. 阶段测试报告

这些文件记录“某一天真实执行过什么、结果如何”，保留事实，不回写改数：

- [reports/README.md](./reports/README.md)
  报告子目录索引。
- [reports/test_report_2026_05_12.md](./reports/test_report_2026_05_12.md)
  V2.1 baseline test report。
- [reports/repeat_navigation_test_report_2026_05_13.md](./reports/repeat_navigation_test_report_2026_05_13.md)
  V2.2 固定任务点与重复导航测试报告。
- [reports/wms_task_points_readiness_report_2026_05_13.md](./reports/wms_task_points_readiness_report_2026_05_13.md)
  WMS readiness 复测报告。
- [reports/collision_monitor_stage1_test_report.md](./reports/collision_monitor_stage1_test_report.md)
  `collision_monitor` stage1 实验记录。

## 4. 诊断说明与日志

这些文件用于解释某一类现象或保留更细的采样过程，不应替代主线设计文档：

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

## 5. 模板与辅助说明

这些文件主要服务于后续继续记录和整理，不直接代表当前主线状态：

- [test-report-template.md](./test-report-template.md)
  通用机器人测试报告模板。
- [repeat_navigation_test_report.md](./repeat_navigation_test_report.md)
  V2.2 重复导航模板。
- [task_points_coordinate_plan.md](./task_points_coordinate_plan.md)
  任务点候选坐标规划说明。
- [resume-bullets.md](./resume-bullets.md)
  对外展示 / 简历素材。

## 6. 当前 WMS 主线判断

截至 `2026-05-13`，当前更准确的结论是：

- 可以接回主线的部分：
  最小 Mock WMS 数据层，即 `config/task_points.yaml` + SQLite + CLI create/list/init 这一层。
- 不建议现在接回主线的部分：
  旧 `future_extensions/wms_integration` 的执行链路、直接发 Nav2 goal 的 task executor、完整调度 / HTTP / MQTT / 多机器人逻辑。

原因很直接：

- 当前 `station_a`、`station_b`、`shelf_1`、`shelf_2` 已有真实 `SUCCEEDED` 证据，足以支撑数据层 intake。
- 但 fresh-session 下 lifecycle / action readiness 仍存在波动，`shelf_1`、`shelf_2` 也出现过有效前置条件下的 `ABORTED`。
- 因此，现在适合把 WMS 保持为“主线可引用的数据层能力”，不适合把完整任务执行链路宣称为当前主线能力。

## 7. 当前整理策略

这次整理已经完成主目录物理分层：

- `docs/reports/`
  放正式测试报告和结果文档。
- `docs/logs/`
  放诊断说明、补测日志和过程记录。

当前仍保留在 `docs/` 顶层的，是主线设计、排障、路线图、模板和辅助说明文档。

这样做的原因是：

- 当前很多文档之间已经互相链接；
- 当前需要优先把“当前主线”“正式结果”“过程日志”三类材料拆开；
- 同时又不希望把设计、模板和长期说明文档埋进过深目录。
