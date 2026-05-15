# Mock WMS Task Flow PRD

日期：`2026-05-14`

## 1. 背景与目标

当前项目已经具备 Gazebo + Nav2 的仓储 AMR 导航验证能力，也已经补上固定任务点、SQLite 任务表、CLI、最小 HTTP API、executor 和 task runner。

这份 PRD 的目标不是定义完整 WMS，而是把现有能力收口为一个更适合展示和验收的最小闭环案例：

- 模拟上层任务创建、任务查询和状态回写
- 复用当前 Nav2 稳定基线执行固定任务点导航
- 证明“任务输入 -> 导航执行 -> 结果回写 -> 测试验收”这条链路已经成立

统一定位：

- 当前主线：AMR 仓储导航 + 最小 Mock WMS 任务执行闭环
- 当前定位：面向物流机器人任务执行、导航验证、测试验收的项目案例
- 当前边界：不是完整 WMS，不是多机器人调度系统，不是生产级后端

## 2. 用户角色 / 使用场景

| 角色 | 关注点 | 当前使用方式 |
| --- | --- | --- |
| 项目经理 / 技术产品经理 | 项目是否具备清晰的最小业务闭环和验收口径 | 阅读 README、PRD、架构图、验收清单和测试报告 |
| 机器人系统集成工程师 | 任务入口是否能安全接回导航基线 | 使用 `publish_initial_pose`、CLI、HTTP API、executor、task runner 做集成验证 |
| 测试 / 验证人员 | 任务创建、执行、状态回写是否可复核 | 按 `docs/acceptance_checklist.md` 和报告入口执行检查 |
| 操作员 / 演示者 | 是否能跑通一条直观的演示链路 | 使用 `docs/guides/mock_wms_visual_demo_recording_guide.md` 或演示脚本 |

## 3. 当前最小功能范围

| 能力模块 | 当前范围 |
| --- | --- |
| 导航基线 | 复用 `launch/navigation.launch.py`、`config/nav2_params.yaml`、`maps/warehouse.yaml`，不在本轮做导航逻辑改造 |
| 固定任务点 | 复用 `config/task_points.yaml` 中已验证点位，当前主线 initial pose 入口为 `start_zone` |
| 任务数据层 | 使用 SQLite 保存最小任务表，支持 `pending / running / succeeded / failed / canceled` |
| CLI 入口 | `init_mock_wms_db`、`create_mock_task`、`list_mock_tasks` |
| HTTP API | `GET /health`、`POST /tasks`、`GET /tasks`、`GET /tasks/{task_id}`、`PATCH /tasks/{task_id}/status` |
| 执行入口 | `mock_wms_executor` 负责单条 pending task，`mock_wms_task_runner` 负责顺序消费 pending 队列 |
| 验证输出 | `test/` 自动化测试、`docs/reports/`、`docs/wms/reports/`、`docs/acceptance_checklist.md` |

## 4. 任务状态流转

对外展示口径建议使用下面这条最小状态流：

```text
PENDING -> RUNNING -> SUCCEEDED
                   -> FAILED
                   -> CANCELED
```

当前主线约束说明：

- CLI / HTTP API 创建任务时，初始状态为 `pending`
- executor 或 task runner 在真正开始执行前，会先通过 ready gate 检查 Nav2 生命周期、TF 和 action server
- 只有在 ready gate 满足后，任务才会进入 `running`
- 导航成功后，任务回写为 `succeeded`
- 导航失败后，任务回写为 `failed`
- 当前实现没有单独的 SQLite `skipped` 状态
- 当 Nav2 未 ready 时，当前主线会保持任务为 `pending`，并把失败原因写入 `status_reason`

## 5. HTTP API 当前边界

当前 HTTP API 只承担最小任务入口和状态回写能力：

- `GET /health`
  用于检查服务可用性，并初始化 SQLite 数据库
- `POST /tasks`
  用于创建一条固定任务点任务
- `GET /tasks`
  用于查询当前任务列表
- `GET /tasks/{task_id}`
  用于查询单条任务详情
- `PATCH /tasks/{task_id}/status`
  用于最小状态回写

当前明确不由 HTTP API 负责的内容：

- 不直接发送 `/navigate_to_pose`
- 不直接控制 `/cmd_vel`
- 不承担常驻调度服务
- 不提供账号、权限、订单、库位、Web 后台

## 6. executor / task runner 的职责边界

| 组件 | 职责 | 当前边界 |
| --- | --- | --- |
| `mock_wms_executor` | 获取最早一条 pending task，并执行 dry-run 或 execute | 一次只处理一条任务；默认 dry-run；只有 `--execute` 且 ready gate 满足时才发送 goal |
| `mock_wms_task_runner` | 顺序消费 pending 队列 | 面向单机器人、单 SQLite 队列；支持 `--max-tasks` 和 `--continue-on-failure`；不做并发调度 |
| `publish_initial_pose` | 把主线 initial pose 注入 Nav2 | 只负责定位入口，不负责任务调度 |
| `mock_wms_api` | 提供最小 HTTP create/query/status-writeback 接口 | 只暴露数据层边界，不直接接管导航执行 |

## 7. 与 Nav2 的关系

- 当前项目的导航执行基线仍然是 `navigation.launch.py` + `config/nav2_params.yaml`
- Mock WMS 任务层只消费固定 `map` frame 目标点，不反向改导航基线
- executor / task runner 通过 Nav2 `NavigateToPose` action 发目标，不直接控制底层运动
- ready gate 会检查 lifecycle、TF 和 `/navigate_to_pose` action server，避免在系统未 ready 时盲目发 goal
- 当前项目案例强调的是“任务执行与导航验证闭环”，不是重新设计 Nav2

## 8. 当前不做什么

- 不做完整 WMS
- 不做多机器人调度
- 不做真实仓库业务系统
- 不做生产级权限、账号、前端后台
- 不做订单、库位、波次、库存、拣选策略
- 不做真实硬件接入、底盘控制器或电机驱动链路

## 9. 验收标准

| 验收主题 | 通过标准 |
| --- | --- |
| 任务创建 | 可以从固定任务点创建 pending 任务，并写入 SQLite |
| 任务查询 | 可以通过 CLI 或 HTTP API 查询任务列表和单条任务 |
| 导航前置检查 | ready gate 能正确识别 lifecycle、TF 和 `/navigate_to_pose` action 可用性 |
| 执行边界 | dry-run 不发送 goal，execute 只有在 ready gate 满足后才发送 goal |
| 状态回写 | 成功任务最终回写为 `succeeded`，失败或未 ready 情况能留下可追溯原因 |
| 可追溯性 | 自动化测试、运行时报告和验收清单之间可以相互引用 |

更细的验收项请看 `docs/acceptance_checklist.md`。

## 10. 后续可扩展方向

- 在不改导航基线的前提下，继续增加 business-point execute 重复验证证据
- 补充更结构化的任务结果输出，例如运行耗时、ready gate 采样、任务批次标识
- 在独立阶段评估常驻服务、队列消费策略、更多 API 边界
- 在未来扩展中再讨论更正式的 WMS / 调度系统，而不是直接并入当前主线
