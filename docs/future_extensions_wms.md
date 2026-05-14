# 未来扩展：WMS 集成（备注）

目的：记录短期 WMS 集成扩展想法，在不修改 V2 导航基线的前提下探索可行方案。

候选扩展清单

- HTTP webhook / 推送式任务下发（用于降低任务下发延迟，作为当前 HTTP 轮询的补充）。
- 基于 Web 的任务查看与编辑界面（小型 FastAPI 服务 + 静态前端，建议放在 `future_extensions/wms_ui`）。
- 持久化远端任务存储（Postgres）与从当前 SQLite mock DB 的迁移路径。
- 多车调度原型（早期草案）：基于租约的任务分配与简单的冲突避让策略。
- 监控与指标导出（Prometheus exporter）：任务吞吐量、队列深度、executor 延迟等指标。

约束

- 在初始集成迭代中请勿修改 `navigation.launch.py`、`maps/warehouse.yaml`、`config/nav2_params.yaml`、机器人模型或 Gazebo 世界文件。
- 倾向于小步、可开关的功能扩展，并保持现有的 `mock_wms_api` 与 `mock_wms_executor` 稳定以便回归测试。

下一步

- 原型：实现一个小型 webhook 接收器，将接收到的任务写入现有的 SQLite-backed API。
- 测试：新增集成测试，验证 webhook -> 创建任务 -> executor dry-run 的完整链路。

