# Project Roadmap

## 1. 文档定位

这份文档用于公开展示项目的**近中期路线图**。

它只保留与当前基线连续、可验证、可逐步交付的内容，不把高不确定性的灵感项混进主线 roadmap。

当前稳定基线仍以 `docs/design.md` 为准。

## 2. 当前状态

当前项目状态：

- V1：AMR 仿真建图最小闭环已完成
- V2：Nav2 导航与路径执行已形成稳定基线
- 测试体系已建立 `data / functional / integration / scenarios` 四层结构
- 已开始补充场景 spec、测试报告模板和轻量 mock WMS

## 3. 当前优先级

### P0：稳定当前导航与验证基线

- [x] 固定 `maps/warehouse.yaml` 为 Nav2 地图入口
- [x] 固定 `launch/navigation.launch.py` + `config/nav2_params.yaml` 为 V2 稳定基线
- [x] 建立 `pytest` 基础测试入口
- [x] 建立场景测试 spec 和测试报告模板
- [ ] 增加第一个 runtime integration test
- [ ] 产出第一份真实测试报告

### P1：把导航验证从“能跑”推进到“可复现”

- [x] 固定 2 到 4 个真实 waypoint 测试点位
- [ ] 跑通短距离导航 smoke test 并沉淀结果
- [ ] 跑通重启后 relocalization regression 并沉淀结果
- [ ] 建立至少一份带截图、指标和结论的验证记录

### P2：把单次导航扩展成最小任务流

- [x] 设计并落地 mock WMS 最小骨架
- [x] 用真实 waypoint 替换 mock WMS 中的 placeholder 点位
- [x] 跑通一条多 step 任务队列
- [ ] 将 mock WMS 输出结果接到测试报告中

## 4. 下一阶段推荐目标

如果当前 P0 和 P1 都稳定，通过以下顺序继续推进最合理：

1. runtime integration tests
2. 场景回归数据积累
3. mock WMS 多任务验证
4. waypoint / task 配置规范化
5. 更正式的任务结果结构化输出

## 5. 当前不纳入主线 roadmap 的内容

以下内容不是不可以做，而是**当前不适合放进主线公开路线图**：

- 本地 LLM 语音调度
- 多机器人协作 / swarm
- 完整 WMS / 订单系统 / 库位系统
- 大规模 CAD 路径控制
- 与当前主线无直接关系的高不确定性实验项

如果未来要探索，建议继续放在 `future_extensions/` 中，以实验草稿形式存在。

## 6. 对外展示建议

如果用于投递简历或作品集介绍，推荐把路线图表达成下面这种节奏：

- 已完成：仿真、SLAM、Nav2、基础测试框架
- 正在推进：runtime integration、场景回归、mock WMS
- 未来计划：更结构化的任务流和验证体系
