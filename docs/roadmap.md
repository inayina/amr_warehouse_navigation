# Project Roadmap

## 1. 文档定位

这份文档用于公开展示项目的**近中期路线图**。

它只保留与当前基线连续、可验证、可逐步交付的内容，不把高不确定性的灵感项混进主线 roadmap。

当前稳定基线仍以 `docs/design.md` 为准。

## 2. 当前状态

当前项目状态：

- V1：AMR 仿真建图最小闭环已完成
- V2：Nav2 导航与路径执行已形成稳定基线
- V2.2：`config/task_points.yaml` 已建立，fixed task points 和重复导航证据正在继续收口
- V3.0：最小 Mock WMS SQLite 数据层与 CLI 已落地，但 executor 不在当前主线
- 测试体系已建立 `data / functional / integration / scenarios` 四层结构
- `pytest test -q` 与 `colcon test --packages-select amr_warehouse_sim` 已接入同一批自动化测试
- 截至 `2026-05-13` 的最新本地校验，`pytest test -q` 为 `25 passed in 0.44s`
- 已形成一份基线测试执行记录：`docs/reports/test_report_2026_05_12.md`
- 已形成 fixed-task-point、startup stability 和 WMS readiness 的多份补充记录
- 当前运行时验证的主要收口点已经从“有没有 initial pose 工具”转为“fresh session 下 startup lifecycle / action readiness 的波动边界”

## 3. 当前优先级

### P0：V2.1 测试与运行时基线收口

- [x] 固定 `maps/warehouse.yaml` 为 Nav2 地图入口
- [x] 固定 `launch/navigation.launch.py` + `config/nav2_params.yaml` 为 V2 稳定基线
- [x] 建立 `pytest` 基础测试入口
- [x] 修复 `colcon test` 对现有 `pytest` 测试的发现与执行
- [x] 建立场景测试 spec 和测试报告模板
- [x] 产出第一份真实测试报告
- [x] 固定 `publish_initial_pose --preset start_zone` 作为主线 initial pose CLI 入口
- [x] 把 initial pose handling 写入 README、design 和 baseline report
- [ ] 继续收口 fresh session 下 lifecycle / action readiness 波动
- [ ] 明确 manual validation、headless validation 与 automated validation 的边界

### P1：V2.2 固定任务点与重复导航验证

- [x] 固定 `start_zone`、station points、shelf points 等任务点集合到 `config/task_points.yaml`
- [x] 建立固定任务点说明和重复导航测试报告
- [x] 为 `station_a`、`station_b`、`shelf_1`、`shelf_2` 记录至少一次真实 `SUCCEEDED` 导航证据
- [ ] 继续为 business points 积累更稳定的 `3~5` 轮重复成功记录
- [ ] 继续记录 `SUCCEEDED / ABORTED / SKIPPED` 与 `/cmd_vel`、TF、lifecycle 的对应关系
- [ ] 形成更适合对外展示的一版截图化 / 指标化汇总

### P2：V3 任务系统与上层调度

- [x] 启动 SQLite / Mock WMS 最小数据层
- [x] 让任务系统只消费固定 map frame 目标点，不直接控制 `/cmd_vel`
- [x] 保持任务层不修改当前 Nav2 参数稳定基线
- [x] 先完成最小任务状态机定义：`pending -> running -> succeeded / failed`
- [ ] 在 V2.1 和 V2.2 进一步收口后，再继续推进 ROS 2 task executor / 更正式的任务执行链路
- [ ] 如有需要，再单独规划 HTTP / 更完整调度层

## 4. 下一阶段推荐目标

如果当前 P0 和 P1 都稳定，通过以下顺序继续推进最合理：

1. 继续收口 fresh-session startup stability
2. 让 business points 积累更稳定的 `3~5` 轮重复成功记录
3. 沉淀可复核的截图、日志和测试报告
4. 在不改 Nav2 基线的前提下推进 ROS 2 task executor
5. 最后再做 waypoint / task 配置规范化和更正式的任务结果结构化输出

## 5. 当前不纳入主线 roadmap 的内容

以下内容不是不可以做，而是**当前不适合放进主线公开路线图**：

- 本地 LLM 语音调度
- 多机器人协作 / swarm
- 在 V2.1 和 V2.2 完成前直接进入完整 WMS / 订单系统 / 库位系统
- 大规模 CAD 路径控制
- 与当前主线无直接关系的高不确定性实验项

如果未来要探索，建议继续放在 `future_extensions/` 中，以实验草稿形式存在。

## 6. 对外展示建议

如果用于投递简历或作品集介绍，推荐把路线图表达成下面这种节奏：

- 已完成：仿真、SLAM、Nav2、自动化测试入口与基线测试报告
- 正在推进：fresh-session startup stability 收口、fixed task points 重复验证、WMS readiness 证据整理
- 未来计划：ROS 2 task executor 和更结构化的任务流 / 上层调度体系
