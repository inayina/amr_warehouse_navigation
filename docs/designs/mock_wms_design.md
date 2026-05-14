# Mock WMS Design

## 1. Purpose

本文件定义 V3.0 Mock WMS 数据层、V3.1 最小任务执行链路、V3.1 最小 HTTP API create/query 入口，以及 V3.3 live ROS / Nav2 顺序任务验证的当前边界。

当前目标不是接管复杂任务调度，而是在不修改 Nav2 稳定基线的前提下，把最小 SQLite 任务入口、最小执行链路和 live 顺序执行证据做成可测试、可追踪的当前主线验证入口。

当前阶段只回答三个问题：

- 如何把一个固定 `map` frame 目标点写成可消费的任务记录
- 如何在不启动 Gazebo / Nav2 / ROS 2 action 的前提下查询这些任务记录
- 如何在不修改 Nav2 主线的前提下，用最小 executor / 顺序 runner 消费 `pending` task

## 2. Scope of V3.0 / V3.1 / V3.3

V3.0 负责最小任务数据层；V3.1 在此基础上补上最小 executor / runner；V3.3 负责把顺序 execute 放到真实 ROS / Nav2 会话里验证。

当前范围包括：

- 使用 SQLite 保存最小任务表
- 使用 CLI 初始化数据库
- 使用 CLI 从 `config/task_points.yaml` 创建 `pending` 任务
- 使用 CLI 查询任务列表
- 使用 FastAPI 暴露最小 `health / create / list / get` REST 接口
- 使用独立执行入口读取最早一条 `pending` task，并执行 dry-run / execute 二选一
- 使用 `ros2 run amr_warehouse_sim mock_wms_task_runner` 在 execute 模式下顺序消费 SQLite `pending` 队列
- 当前允许使用已完成真实 Nav2 goal 验证的 `candidate_dock_a`、`station_a`、`station_b`、`shelf_1`、`shelf_2`；其中 `dock_a` 继续作为 `candidate_dock_a` 的兼容输入
- 已完成 `station_a` 单条 execute live 验证，以及 `station_a -> station_b` 两条顺序 execute live 验证

## 3. Out of Scope

本轮明确不做以下内容：

- 不直接控制 `/cmd_vel`
- 不做常驻 ROS 2 调度服务
- 不做超出当前 `health / create / list / get` 范围的更完整 HTTP 调度服务
- 不做 MQTT
- 不做多机器人调度
- 不把 `future_extensions/` 的旧 WMS 执行链路直接接回当前主线

## 4. Data Model

当前 SQLite 数据库路径默认是：

```text
data/mock_wms.db
```

当前任务表：

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | 任务主键 |
| `task_name` | `TEXT` | 人类可读的任务名 |
| `target_name` | `TEXT` | 固定目标点名称，写入当前主线实际解析后的点名 |
| `frame_id` | `TEXT` | 当前固定为 `map` |
| `x` | `REAL` | 目标点 X |
| `y` | `REAL` | 目标点 Y |
| `yaw` | `REAL` | 目标点偏航角 |
| `status` | `TEXT` | 当前受限于 `pending / running / succeeded / failed / canceled` |
| `status_reason` | `TEXT` | 当前状态对应的最近一次说明，例如 ready gate 未满足原因或 goal 结果 |
| `created_at` | `TEXT` | 任务创建时间，UTC ISO8601 |
| `updated_at` | `TEXT` | 最近更新时间，UTC ISO8601 |

说明：

- Mock WMS 当前只存储 `map` frame goal
- 当前不存储路径、速度、控制器参数，也不记录 `/cmd_vel`
- `status_reason` 只用于记录最近一次状态回写原因，不替代独立运行日志
- 当前 `dock_a` 只是兼容输入别名；如果主线配置仍是 `candidate_dock_a`，数据库内会写入当前实际解析到的主线点名
- `station_a`、`station_b`、`shelf_1`、`shelf_2` 的坐标来自 `docs/task_points_coordinate_plan.md` 的 candidate coordinates，并已在 `2026-05-13` fresh session 中拿到至少一次真实 `SUCCEEDED` 导航结果

## 5. Task State Machine

当前最小状态机如下：

```text
pending
  -> running
  -> canceled

running
  -> succeeded
  -> failed
  -> canceled
```

当前说明：

- 本轮 CLI 只创建 `pending` 任务
- V3.1 最小 executor 在 ready gate 不满足时，会保持任务为 `pending`，同时更新 `status_reason`
- V3.1 顺序 runner 只会在 execute 模式下连续消费队列；dry-run 仍只检查最早一条 `pending` task
- `running / succeeded / failed / canceled` 为后续执行器使用
- 当前数据层只约束“允许出现的状态值”和最近一次原因，不实现完整调度器

## 6. Relationship with Nav2

Mock WMS 当前与 Nav2 的关系已从“只提供输入”推进到“允许实验性最小执行器消费一条 pending task”，但仍不是完整任务系统。

- Mock WMS 只存储固定 `map` frame goal
- `ros2 run amr_warehouse_sim mock_wms_executor` 会在独立边界内读取最早一条 `pending` task
- `ros2 run amr_warehouse_sim mock_wms_task_runner --execute` 会在同一边界内顺序消费当前 SQLite `pending` 队列
- 默认模式仍然是 dry-run；dry-run 只检查 ready gate，不发送 `/navigate_to_pose` goal
- 只有显式传入 `--execute`，执行器或顺序 runner 才会在 ready gate 满足后发送 `/navigate_to_pose`
- 当前仍不声明 SQLite -> Nav2 已完全稳定闭环
- `2026-05-13` fresh session live 记录已经确认：`station_a` 单条 execute 成功，`station_a` 与 `station_b` 顺序 execute 成功，SQLite `status` 最终回写为 `succeeded`

## 7. Relationship with Fixed Task Points

当前主线固定点入口仍然是：

```text
config/task_points.yaml
```

当前约束：

- Mock WMS 只能读取现有 `config/task_points.yaml`
- 当前允许 `candidate_dock_a` / `dock_a`、`station_a`、`station_b`、`shelf_1`、`shelf_2` 创建 `pending` 任务
- `start_zone` 继续只作为 initial pose 入口，不作为当前 V3 任务目标
- `station_a`、`station_b`、`shelf_1`、`shelf_2` 当前仍标记为 candidate coordinates，不代表最终仓库业务点位已定版
- 如果未来正式把 `candidate_dock_a` 重命名为 `dock_a`，当前 CLI 兼容层仍可继续工作

## 8. Current Limitation

当前限制需要明确写出：

- V3.3 live 验证已经完成，但不代表端到端任务执行已经完全稳定
- 当前已有最小 HTTP API，但仍没有 MQTT、Web UI 或更完整调度服务
- 当前没有常驻 ROS 2 task executor 服务，只有单次 executor 和顺序 runner
- 当前顺序 runner 只支持单机器人、单 SQLite 队列、顺序执行，不做抢占、并发和复杂重试
- 当前不会直接驱动机器人，也不会直接控制 `/cmd_vel`
- 因 V2.2 仍存在 lifecycle 偶发波动，V3.1 不声明端到端任务执行已经完全稳定
- `2026-05-13` live 现场的唯一 CLI 差异曾是 `init_mock_wms_db`、`create_mock_task`、`list_mock_tasks` 没有统一注册为 `ros2 run` 入口；本轮只做这项注册一致性收尾，不改变 executor / runner 主逻辑

## 9. Current Mainline Decision

截至 `2026-05-13`，当前关于“WMS 是否可以接回主线”的结论应明确写成两层：

### 9.1 可以接回主线的部分

以下部分可以视为当前主线的配套能力：

- `config/task_points.yaml` 作为固定任务点输入
- SQLite 最小任务表
- `ros2 run amr_warehouse_sim init_mock_wms_db`、`create_mock_task`、`list_mock_tasks`
- `uvicorn scripts.mock_wms_api:create_app --factory` 的最小 HTTP create/query/status-writeback 入口
- `ros2 run amr_warehouse_sim mock_wms_executor` 的单条 task ready-gate / execute 入口
- `ros2 run amr_warehouse_sim mock_wms_task_runner` 的顺序 pending-queue execute 入口
- 对 `candidate_dock_a` / `dock_a`、`station_a`、`station_b`、`shelf_1`、`shelf_2` 的 pending-task 创建能力
- `station_a` 单条 execute live 记录，以及 `station_a -> station_b` 顺序 execute live 记录

原因：

- 这些点位已经有真实导航验证记录支撑
- 对应数据层有自动化测试和 CLI smoke test
- 这部分不会反向修改 `navigation.launch.py`、`config/nav2_params.yaml` 或底层控制链

### 9.2 暂不接回主线的部分

以下部分当前仍不建议直接接回主线或对外宣称为“已完成调度系统”：

- 旧 `future_extensions/wms_integration` 执行链路
- 更完整 HTTP 调度服务 / MQTT / Web UI / 调度服务
- 多机器人或更复杂的任务编排
- 常驻 task service、复杂重试策略和并发任务协调

原因：

- 当前 fresh-session 下 lifecycle / action readiness 仍存在波动
- business points 虽已有 `SUCCEEDED` 证据，但仍出现过真实 `SKIPPED` / `ABORTED`
- 因此现在更适合把 WMS 表述为“主线可复核的最小任务链路”，而不是对外宣称为“完整主线调度系统”

### 9.3 如果下一步要继续推进

建议顺序：

1. 保持当前 SQLite + fixed task points 在主线文档中继续可见
2. 保持 CLI 入口与 live validation 文档一致，不再把 `python3 scripts/...` 当成唯一主线入口
3. 继续累计 business points 的重复成功记录
4. 只有在 startup stability 波动被更好约束后，再考虑把任务链从“最小 runner”推进到更正式的服务态
