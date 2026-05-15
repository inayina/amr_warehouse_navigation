# Project Roadmap

## 1. 文档定位

这份文档用于公开展示项目的**近中期路线图**。

它只保留与当前基线连续、可验证、可逐步交付的内容，不把高不确定性的灵感项混进主线 roadmap。

当前稳定基线仍以 `docs/design.md` 为准。

## 2. 当前状态

截至 `2026-05-14`，当前主线对外统一口径如下：

- 当前主线：AMR 仓储导航 + 最小 Mock WMS 任务执行闭环
- 当前定位：面向物流机器人任务执行、导航验证、测试验收的项目案例
- 当前边界：不是完整 WMS，不是多机器人调度系统，不是生产级后端

当前项目状态：

- V1：AMR 仿真建图最小闭环已完成
- V2：Nav2 导航与路径执行已形成稳定基线
- V2.2：`config/task_points.yaml`、重复导航证据和 WMS readiness 入口已形成一版可复核基线
- V3：最小 Mock WMS SQLite 数据层、CLI、executor / task runner 与 HTTP API 已落地
- V3：live ROS / Nav2 顺序任务执行验证已完成，`station_a` 单条 execute 与 `station_a -> station_b` 顺序 execute 均已拿到真实 `SUCCEEDED`
- 测试体系已建立 `data / functional / integration / scenarios` 四层结构
- `pytest test -q` 与 `colcon test --packages-select amr_warehouse_sim` 已接入同一批自动化测试
- 截至 `2026-05-14` 的最新本地校验，从项目根目录执行 `make test` 的结果为 `63 passed`
- 已形成一份基线测试执行记录：`docs/reports/test_report_2026_05_12.md`
- 已形成 fixed-task-point、startup stability 和 WMS readiness 的多份补充记录
- 已补一份 V2.1 / V2.2 收口记录：`docs/reports/v2_validation_closure_2026_05_13.md`
- 当前运行时验证的主要关注点已经从“有没有 initial pose 工具”转为“把 ready gate 波动边界固定到 headless 可复核流程”

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
- [x] 收口 fresh session 下 lifecycle / action readiness 波动边界
- [x] 明确 manual validation、headless validation 与 automated validation 的边界

### P1：V2.2 固定任务点与重复导航验证

- [x] 固定 `start_zone`、station points、shelf points 等任务点集合到 `config/task_points.yaml`
- [x] 建立固定任务点说明和重复导航测试报告
- [x] 为 `station_a`、`station_b`、`shelf_1`、`shelf_2` 记录至少一次真实 `SUCCEEDED` 导航证据
- [x] 按 business-point 集合口径积累 `3~5` 轮以上真实重复成功记录
- [x] 记录 `SUCCEEDED / ABORTED / SKIPPED` 与 `/cmd_vel`、TF、lifecycle 的对应关系
- [x] 形成一版对外可复核的指标化汇总

### P2：V3 最小 Mock WMS 任务执行闭环

- [x] 启动 SQLite / Mock WMS 最小数据层
- [x] 让任务系统只消费固定 map frame 目标点，不直接控制 `/cmd_vel`
- [x] 保持任务层不修改当前 Nav2 参数稳定基线
- [x] 先完成最小任务状态机定义：`pending -> running -> succeeded / failed`
- [x] 在 V2.1 和 V2.2 收口后，继续推进 ROS 2 task executor / 更正式的任务执行链路
- [x] 完成 V3.3 live ROS / Nav2 顺序任务执行验证，确认 dry-run 不发送 goal，execute 会在 ready gate 后发送 `/navigate_to_pose`
- [x] 统一 `init_mock_wms_db`、`create_mock_task`、`list_mock_tasks`、`mock_wms_executor`、`mock_wms_task_runner` 的主线 CLI 入口
- [x] 完成最小 Mock WMS HTTP API `health / create / list / get` 闭环，并保持它只暴露 SQLite 数据层
- [ ] 如有需要，再单独规划常驻服务 / 更完整调度层，但不并入当前项目主线定位

## 4. 下一阶段推荐目标

当前 P0 和 P1 的测试收口已完成，下一阶段继续推进最合理的顺序是：

1. 继续观察 fresh-session startup stability，但不再把它作为 V2.1/V2.2 未完成项
2. 继续沉淀可复核的截图、日志和测试报告
3. 在不改 Nav2 基线的前提下，继续沉淀更多 business-point execute 重复成功证据
4. 再做 waypoint / task 配置规范化、更多 business-point execute 证据，以及更正式的任务结果结构化输出

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

- 已完成：仓储 AMR 仿真、SLAM、Nav2 稳定基线与固定任务点导航验证
- 已完成：最小 Mock WMS 任务创建 / 查询 / 执行 / 状态回写闭环
- 已完成：自动化测试入口、运行时验证报告与验收文档收口
- 当前边界：项目案例聚焦任务执行与导航验证，不宣称完整 WMS 或生产调度系统
- 未来计划：在不破坏导航基线的前提下，继续扩展更正式的任务流与调度边界
