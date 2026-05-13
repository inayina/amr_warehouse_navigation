# Mock WMS Design

## 1. Purpose

本文件定义 V3.0 Mock WMS 的最小任务数据层边界。

当前目标不是接管导航执行，而是先为后续任务执行器准备一份稳定、可测试、可追踪的任务存储入口。

当前阶段只回答两个问题：

- 如何把一个固定 `map` frame 目标点写成可消费的任务记录
- 如何在不启动 Gazebo / Nav2 / ROS 2 action 的前提下查询这些任务记录

## 2. Scope of V3.0

V3.0 当前只做任务数据层，不接 Nav2 action executor。

当前范围包括：

- 使用 SQLite 保存最小任务表
- 使用 CLI 初始化数据库
- 使用 CLI 从 `config/task_points.yaml` 创建 `pending` 任务
- 使用 CLI 查询任务列表
- 当前允许使用已完成真实 Nav2 goal 验证的 `candidate_dock_a`、`station_a`、`station_b`、`shelf_1`、`shelf_2`；其中 `dock_a` 继续作为 `candidate_dock_a` 的兼容输入

## 3. Out of Scope

本轮明确不做以下内容：

- 不发送 Nav2 goal
- 不直接控制 `/cmd_vel`
- 不启动 ROS 2 task executor
- 不做 HTTP API
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
| `created_at` | `TEXT` | 任务创建时间，UTC ISO8601 |
| `updated_at` | `TEXT` | 最近更新时间，UTC ISO8601 |

说明：

- Mock WMS 当前只存储 `map` frame goal
- 当前不存储路径、速度、控制器参数，也不记录 `/cmd_vel`
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
- `running / succeeded / failed / canceled` 为后续执行器预留
- 当前数据层只约束“允许出现的状态值”，不实现完整调度器

## 6. Relationship with Nav2

Mock WMS 当前与 Nav2 的关系是“只提供输入，不负责执行”。

- Mock WMS 只存储固定 `map` frame goal
- 后续 ROS 2 task executor 才会消费 `pending` task，并将其转换为 Nav2 goal
- 当前 V3.0 不直接调用 `NavigateToPose`
- 当前 V3.0 不声明 SQLite -> Nav2 已闭环

## 7. Relationship with Fixed Task Points

当前主线固定点入口仍然是：

```text
config/task_points.yaml
```

当前约束：

- Mock WMS 只能读取现有 `config/task_points.yaml`
- 当前允许 `candidate_dock_a` / `dock_a`、`station_a`、`station_b`、`shelf_1`、`shelf_2` 创建 `pending` 任务
- `start_zone` 继续只作为 initial pose 入口，不作为当前 V3.0 任务目标
- `station_a`、`station_b`、`shelf_1`、`shelf_2` 当前仍标记为 candidate coordinates，不代表最终仓库业务点位已定版
- 如果未来正式把 `candidate_dock_a` 重命名为 `dock_a`，当前 CLI 兼容层仍可继续工作

## 8. Current Limitation

当前限制需要明确写出：

- V3.0 只完成任务数据层，不代表端到端任务执行已经完成
- 当前没有 HTTP、MQTT、Web UI 或调度服务
- 当前没有 ROS 2 task executor，因此不会自动消费 `pending` 任务
- 当前不会直接驱动机器人，也不会直接控制 `/cmd_vel`
- 因 V2.2 仍存在 lifecycle 偶发波动，V3.0 不声明端到端任务执行已经完全稳定

## 9. Current Mainline Decision

截至 `2026-05-13`，当前关于“WMS 是否可以接回主线”的结论应明确写成两层：

### 9.1 可以接回主线的部分

以下部分可以视为当前主线的配套能力：

- `config/task_points.yaml` 作为固定任务点输入
- SQLite 最小任务表
- `init_mock_wms_db.py`、`create_mock_task.py`、`list_mock_tasks.py`
- 对 `candidate_dock_a` / `dock_a`、`station_a`、`station_b`、`shelf_1`、`shelf_2` 的 pending-task 创建能力

原因：

- 这些点位已经有真实导航验证记录支撑
- 对应数据层有自动化测试和 CLI smoke test
- 这部分不会反向修改 `navigation.launch.py`、`config/nav2_params.yaml` 或底层控制链

### 9.2 暂不接回主线的部分

以下部分当前仍不建议直接接回主线：

- 旧 `future_extensions/wms_integration` 执行链路
- 直接消费 pending task 并发送 Nav2 goal 的 ROS 2 task executor
- HTTP / MQTT / Web UI / 调度服务
- 多机器人或更复杂的任务编排

原因：

- 当前 fresh-session 下 lifecycle / action readiness 仍存在波动
- business points 虽已有 `SUCCEEDED` 证据，但仍出现过真实 `SKIPPED` / `ABORTED`
- 因此现在更适合把 WMS 保持为“数据层和任务输入层”，而不是对外宣称为“主线端到端任务执行层”

### 9.3 如果下一步要继续推进

建议顺序：

1. 保持当前 SQLite + fixed task points 在主线文档中继续可见
2. 不修改 Nav2 稳定基线，单独验证 ROS 2 task executor
3. 继续累计 business points 的重复成功记录
4. 只有在 startup stability 波动被更好约束后，再考虑把 executor 从实验态推进到主线态
