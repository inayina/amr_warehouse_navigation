# EMS / Fleet Architecture Audit

日期：`2026-08-17`  
审计对象：仓库 `inayina/amr_warehouse_navigation`（ROS 2 包名 `amr_warehouse_sim`）HEAD  
审计范围：Stage 0 只读审计。本文件是后续 Robot Registry / Fleet Dispatcher / 多机器人仿真的设计输入，**不是实现说明书**。

HEAD 快照：

```text
branch: main
commit:  c57ae1c401b320118d8cce92db08f2ff6ce87c4d
subject: docs:整理项目文档
date:    2026-05-27
pytest:  63 tests collected
```

本轮明确结论：

- 当前仓库已经有一条可复核的**单机器人**任务闭环：Mock WMS → SQLite / FastAPI → executor / task runner → Nav2 ready gate → NavigateToPose → Gazebo AMR → status writeback。
- 当前仓库**没有** Robot Registry、Fleet Dispatcher、Assignment、Heartbeat、Resource Lock，也没有 namespaced 多机器人 Nav2。
- 后续最小 EMS 层应作为新模块加在 Mock WMS 和 Robot Executor 之间，而不是把调度逻辑继续塞进 `tasks` 表或 `mock_wms_executor`。
- Stage 1–5 应先用 **in-process / simulated execution context** 验证调度语义；Stage 6 的真实双 Nav2 stack 风险高，必须 opt-in，不得替换现有 `navigation.launch.py`。

---

## 1. 文档定位

本文件回答四个问题：

1. 当前 HEAD 实际长什么样？
2. 工业 AMR 中的 WMS / EMS / Robot Executor / Nav2 分别对应本仓库哪些组件？
3. 单机器人假设具体嵌在哪些文件、字段、话题和坐标系里？
4. 最小 Fleet / EMS 应按什么顺序落地，哪些改动会破坏 V1 / V2 / V3 稳定基线？

阅读约定：

- 当前主线设计仍以 `docs/design.md` 为准。
- 当前 Mock WMS 边界仍以 `docs/designs/mock_wms_design.md` 和 `docs/prd_mock_wms_task_flow.md` 为准。
- `future_extensions/wms_integration/` 是 legacy 样例，**不是**本轮 Fleet Dispatcher 的实现起点。
- 本文件中的 “demo-level” 一律表示教学 / 演示语义，不等于生产恢复语义。

---

## 2. 当前架构（As-Is）

### 2.1 当前真实链路

```text
Operator / Dashboard
    │
    ├─ CLI: init_mock_wms_db / create_mock_task / list_mock_tasks
    └─ FastAPI: POST /tasks, GET /tasks, PATCH /tasks/{id}/status
                │
                ▼
         SQLite tasks 表
         data/mock_wms.db
                │
                ▼
     mock_wms_executor          一次取最早一条 pending
     mock_wms_task_runner       顺序消费同一条队列
                │
                ▼
     Nav2 ready gate
     /map_server /amcl /planner_server /controller_server /bt_navigator
     TF map -> odom
     action /navigate_to_pose
                │
                ▼
     Nav2 planner / controller / BT
     /cmd_vel
                │
                ▼
     Gazebo model://my_robot
     /scan /odom /tf
                │
                ▼
     SQLite / HTTP status writeback
     pending | running | succeeded | failed | canceled
```

当前系统里**没有**下面这一层：

```text
WMS business task
        │
        ▼
EMS / Fleet Dispatcher     ← 缺失
        │
        ▼
per-robot execution context
```

今天的 executor 同时承担了三件事：取任务、判断能不能跑、对唯一一台机器人发 NavigateToPose。这在单车验证里是合理的；在 Fleet / EMS 学习目标里，这三件事必须拆开。

### 2.2 当前组件地图

| 层 | 当前组件 | 文件 | 实际职责 |
| --- | --- | --- | --- |
| 业务任务入口 | Mock WMS CLI / HTTP | `amr_warehouse_sim/create_mock_task.py`、`amr_warehouse_sim/mock_wms_api.py` | 创建 / 查询一条固定点导航任务 |
| 任务存储 | SQLite `tasks` | `amr_warehouse_sim/mock_wms_db_common.py` | 只存一个 `map` frame goal 和任务状态 |
| 任务消费 | executor | `amr_warehouse_sim/mock_wms_executor.py` | FIFO 取最早 `pending`，检查全局 Nav2，发一个 goal |
| 队列循环 | task runner | `amr_warehouse_sim/mock_wms_task_runner.py` | 单队列顺序循环调用 executor |
| 点位字典 | 固定任务点 | `config/task_points.yaml` | 名称 → `map` frame `(x, y, yaw)` |
| 定位入口 | initial pose | `amr_warehouse_sim/initial_pose_publisher.py` | 向 `/initialpose` 注入 `start_zone` |
| 导航 | Nav2 bringup | `launch/navigation.launch.py`、`config/nav2_params.yaml` | 无 namespace 的单栈 Nav2 |
| 仿真 | Gazebo world include | `worlds/warehouse_full.world`、`models/my_robot/model.sdf` | 只 include 一台 `my_robot` |
| 桥接 | ros_gz_bridge | `launch/simulation.launch.py` | 全局 `/cmd_vel` `/odom` `/scan` `/clock` |
| TF | odom TF + lidar TF | `amr_warehouse_sim/odom_tf_node.py`、`simulation.launch.py` | 硬编码 `odom -> base_link` 和 `my_robot/lidar_link/lidar` |

### 2.3 当前明确不是什么

仓库 README、`docs/design.md`、`docs/prd_mock_wms_task_flow.md` 已经写清楚：

- 不是完整 WMS
- 不是多机器人调度系统
- 不是生产级后端
- 不直接控制 `/cmd_vel`
- 不做订单 / 库位 / 权限 / Web 后台

这次审计确认：这些边界与 HEAD 代码一致，不是文档过时。

---

## 3. 十项 HEAD 审计结果

### 3.1 Mock WMS task schema

当前任务不是“搬运任务”，而是**单点导航任务**。

创建入口只接受：

```text
target_name   必填，必须能在 config/task_points.yaml 中解析
task_name     可选
```

落库后的任务记录：

| 字段 | 含义 | 对 Fleet 的影响 |
| --- | --- | --- |
| `id` | SQLite 主键 | 可以继续作为 WMS task_id |
| `task_name` | 人类可读名 | 可保留 |
| `target_name` | 单个目标点名 | **没有 pickup / dropoff** |
| `frame_id` | 固定为 `map` | 可保留 |
| `x / y / yaw` | 解析后的目标位姿 | 这是 Nav2 goal，不是业务语义 |
| `status` | `pending / running / succeeded / failed / canceled` | 这是 WMS 任务状态，也被当成执行状态使用 |
| `status_reason` | 最近一次原因 | 不是事件日志，会被覆盖 |
| `created_at / updated_at` | UTC ISO8601 | 可保留 |

当前允许的 V3 目标名：

```text
candidate_dock_a / dock_a（别名）
station_a
station_b
shelf_1
shelf_2
```

`start_zone` 只作为 initial pose，**不能**创建 Mock WMS 任务。

缺失字段（Fleet 需要，但当前没有）：

```text
pickup
dropoff
priority
assigned_robot_id
assigned_at
dispatch_reason / cost
```

工业含义：今天的 Mock WMS 已经接近 “有一个业务点需要去”，但还不是 “从 A 取货送到 B”。Stage 3 应扩展业务任务模型，而不是继续把 `target_name` 假装成完整搬运单。

### 3.2 SQLite 数据模型

默认库路径：`data/mock_wms.db`。

当前只有一张表：

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    target_name TEXT NOT NULL,
    frame_id TEXT NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    yaw REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'running', 'succeeded', 'failed', 'canceled'
    )),
    status_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status_created_at
    ON tasks(status, created_at);
```

观察：

- `initialize_database()` 有轻量 schema migration：缺 `status_reason` 时 `ALTER TABLE`。
- 状态约束只检查**允许的枚举值**，不检查**合法转移**。`PATCH /tasks/{id}/status` 可以把 `succeeded` 改回 `pending`。
- 没有 `robots`、`assignments`、`resources`、`heartbeats`、`events` 表。
- `get_next_pending_task()` 是全局 FIFO：`ORDER BY created_at ASC, id ASC LIMIT 1`。这是队列，不是调度器。

结论：SQLite 可以继续做本地持久化，但 Fleet 状态不能继续挤进 `tasks.status` 这一个字段。

### 3.3 FastAPI task API

实现：`amr_warehouse_sim/mock_wms_api.py`  
启动：`uvicorn scripts.mock_wms_api:create_app --factory --host 127.0.0.1 --port 8000`

当前路由：

| Method | Path | 作用 |
| --- | --- | --- |
| `GET` | `/health` | 初始化 DB，返回 `db_path` / `task_points_path` |
| `POST` | `/tasks` | 按 `target_name` 创建 pending task |
| `GET` | `/tasks` | 返回 `{count, tasks}` |
| `GET` | `/tasks/{task_id}` | 单条查询 |
| `PATCH` | `/tasks/{task_id}/status` | 任意允许状态回写 |

当前 API **没有**：

```text
GET  /robots
GET  /robots/{robot_id}
POST /robots/{robot_id}/heartbeat
GET  /fleet/tasks
GET  /fleet/assignments
```

边界判断：

- `/tasks` 应继续表示 **WMS 业务任务**，不要改成 `/tasks2`。
- executor 已经能通过 `--api-base-url` 走 HTTP 拉 pending 并 PATCH 状态。
- `mock_wms_task_runner` **没有** HTTP 模式，只走 SQLite / executor 默认路径。
- HTTP dry-run 和 SQLite dry-run 语义不一致，见 3.4。这是后续必须先统一或显式分叉的点。

### 3.4 `mock_wms_executor`

这是当前最关键、也最需要抽象的组件。

职责现状：

1. 取最早一条 `pending`（SQLite 或 HTTP）。
2. 用 `target_name` 解析 pose。
3. 检查**全局** Nav2 ready gate。
4. `--execute` 时对 `/navigate_to_pose` 发一个 goal。
5. 把结果写回同一条 task 的 `status`。

Ready gate 硬编码：

```text
/map_server
/amcl
/planner_server
/controller_server
/bt_navigator
map -> odom
/navigate_to_pose
```

Action 默认名：`/navigate_to_pose`。  
ROS node 名：`mock_wms_executor`。  
没有 `robot_id`，没有 namespace，没有 per-robot action client。

状态机（SQLite 路径）：

```text
no pending          -> no-op
invalid target      -> failed
ready gate false    -> 保持 pending + status_reason
dry-run ready       -> 保持 pending + status_reason
execute ready       -> running -> succeeded | failed
```

状态机（HTTP 路径，注意差异）：

```text
HTTP dry-run
  pending -> running -> succeeded
  原因：本地模拟，不发送 Nav2 goal

HTTP execute
  与 SQLite execute 类似：ready gate 失败保持 pending
  ready 后 running -> succeeded | failed
```

这个差异很重要：HTTP dry-run 已经把任务写成终态 `succeeded`，SQLite dry-run 则故意保持 `pending` 以便重试。Fleet 层如果复用 HTTP dry-run 语义，会把“模拟成功”和“真实导航成功”混在一起。

已经存在、应被复用的抽象：

```text
ExecutorRuntime Protocol
  check_ready_gate()
  navigate_to_pose(pose, timeout_sec)
  close()
```

测试里的 `FakeRuntime` 已经证明：调度 / 状态机可以在不启动 Gazebo / Nav2 的情况下验证。Stage 1–5 应把这个 Protocol 升级为 **per-robot execution context**，而不是复制 launch 文件。

### 3.5 `mock_wms_task_runner`

这是单机器人顺序队列循环，不是 fleet manager。

行为：

- dry-run：只看最早一条 pending，然后停。
- execute：循环调用 `run_executor_once()`，直到队列空、`max-tasks`、ready-gate timeout，或遇到 `failed / invalid-target`。
- `--continue-on-failure` 只是“失败后继续下一条”，不是重分配。
- 默认 action 仍是 `/navigate_to_pose`。
- 不支持 `--api-base-url`。

文档自己的口径已经正确：`面向单机器人、单 SQLite 队列；不做并发调度`。

### 3.6 `task_points.yaml`

当前点位：

| 名称 | `(x, y, yaw)` | 当前用途 |
| --- | --- | --- |
| `start_zone` | `(0.0, 0.0, 0.0)` | 唯一主线 initial pose，对应 world 出生点 |
| `station_a` | `(-5.3, -5.8, 3.14)` | 可创建任务；候选充电站接近点 |
| `station_b` | `(5.0, -4.8, 0.0)` | 可创建任务；候选打包站接近点 |
| `shelf_1` | `(-2.75, 2.5, 0.0)` | 可创建任务；左侧货架接近点 |
| `shelf_2` | `(2.75, 2.5, 3.14)` | 可创建任务；右侧货架接近点 |
| `candidate_dock_a` | `(0.0, -3.8, -1.57)` | 可创建任务；历史候选点 |

对 Fleet 的价值：

- 已经具备 **station 名称抽象**，足够做第一版 assignment cost。
- 不需要为了算距离去订阅实时 `/amcl_pose` 或改 Nav2。
- 第一版可以把 robot 的 `current_station` 设成这些名字之一，用静态距离：

```text
cost(robot, pickup) ≈ hypot(robot_station.xy - pickup.xy)
```

注意：这些点仍被文档标记为 candidate coordinates，不是最终业务库位。Fleet demo 可以继续用它们当逻辑站点，但不要宣称已经完成仓库 layout 定版。

### 3.7 Nav2 launch / namespace / action client

`launch/navigation.launch.py` 的关键事实：

- Include `nav2_bringup/launch/bringup_launch.py`。
- **没有** `namespace` / `use_namespace` launch argument。
- `use_composition: False`。
- 延迟 6 秒后启动 laser_filters、robot_state_publisher、Nav2、RViz。
- laser remaps 是全局 `/scan` → `/scan_filtered`。
- RViz 使用 `models/my_robot_visual.urdf`，link 名是 `base_link`。

`config/nav2_params.yaml` 的坐标系 / 话题：

```text
AMCL
  global_frame_id: map
  odom_frame_id: odom
  base_frame_id: base_link
  scan_topic: /scan_filtered

bt_navigator
  global_frame: map
  robot_base_frame: base_link
  odom_topic: /odom
  navigators: navigate_to_pose, navigate_through_poses

controller / velocity_smoother
  cmd_vel_out_topic: cmd_vel

collision_monitor
  enabled: False
```

executor 的 action client 订阅的是绝对名 `/navigate_to_pose`。  
lifecycle 查询的是绝对名 `/map_server/get_state` 等。

测试契约 `test/integration/test_navigation_pipeline_contract.py` 把这些全局名字写成了回归断言。任何 namespaced 改动如果不 opt-in，会直接打红现有测试。

`launch/slam.launch.py` 同样 `namespace=''`，`base_frame: base_link`。V1 建图栈也是单机器人全局 TF。

### 3.8 Gazebo robot model 和 spawn 方式

机器人不是 `spawn_entity` 动态生成的，而是写死在 world 里：

```xml
<!-- worlds/warehouse_full.world -->
<include>
  <uri>model://my_robot</uri>
  <name>my_robot</name>
  <pose>0 0 0 0 0 0</pose>
</include>
```

模型：`models/my_robot/model.sdf`

- 差速插件 `gz::sim::systems::DiffDrive`
- 控制话题：`/cmd_vel`
- 里程计话题：`/odom`
- `frame_id: odom`
- `child_frame_id: base_link`
- 雷达 sensor topic：`/scan`

`launch/simulation.launch.py` 的 bridge 也是全局的：

```text
/cmd_vel
/odom
/scan
/clock
```

静态 TF：

```text
base_link -> my_robot/lidar_link/lidar
```

`odom_tf_node` 订阅 `/odom`，发布 `odom -> base_link`。在收到第一帧 odom 前，会发布 identity TF，并警告检查 `my_robot` 是否 spawn。

仓库地面约 `24 x 24`，货架通道存在，物理上放得下第二台车；但当前 spawn、话题、TF、插件全部按一台车设计。复制模型而不改 topic / frame / model name，会立刻发生话题碰撞和 TF 碰撞。

### 3.9 当前单机器人状态如何表示

当前**没有**机器人对象。

“机器人忙不忙”只能从任务表间接看：

```text
存在 status=running 的 task  → 隐含唯一那台车 BUSY
没有 running task            → 隐含 IDLE
没有 heartbeat               → 不存在 OFFLINE
没有 ERROR 字段              → Nav2 ABORTED 只表现为 task=failed
```

更细的现状：

| 需要的 Fleet 状态 | 当前替代物 | 缺口 |
| --- | --- | --- |
| `robot_id` | 硬编码 `my_robot` / 无字段 | 无法表达 robot_01 / robot_02 |
| `IDLE / ASSIGNED / BUSY` | `tasks.status` | 任务状态和机器人状态混在一起 |
| `current_task_id` | 扫描 `status=running` 的那一行 | 没有唯一性约束 |
| `current_station / pose` | 无。AMCL 有实时位姿，但任务层不读 | 调度层没有 station 抽象 |
| `last_heartbeat` | 无 | 无法做 OFFLINE |
| `battery` | 无 | 可模拟，当前不存在 |

Nav2 / 仿真侧“机器人还活着”的信号是：

- `/odom` 是否到达
- lifecycle 是否 `active`
- `map -> odom` 是否存在
- `/navigate_to_pose` action server 是否可用

这些是 **Nav2 健康信号**，不是 Fleet robot registry。Stage 1 不应直接把 lifecycle 查询当成 robot state machine。

### 3.10 当前测试和稳定基线

自动化：

```text
make test
→ python3 -m pytest test -q
→ HEAD 可收集 63 tests
CI: .github/workflows/python-test.yml 对 main/master 跑同一入口
```

分层：

| 层 | 覆盖 | 对 Fleet 的含义 |
| --- | --- | --- |
| `test/data/` | 地图、Nav2 参数、task_points | Stage 6 改 launch/params 会碰到这里 |
| `test/functional/` | launch smoke、initial pose | 保护 `navigation.launch.py` 可生成 |
| `test/integration/` | Mock WMS DB / HTTP / executor / runner / 导航契约 | Stage 1–5 的回归锚点 |
| `test/scenarios/` | 手工运行时 spec，不进 pytest | 单车 live 证据，不是 fleet 测试 |

executor 测试已经用 `FakeRuntime` 覆盖：

- 无 pending
- 非法 target
- ready gate false
- dry-run 不发 goal
- execute succeeded / failed
- HTTP 拉任务和状态回写

task runner 测试覆盖：

- dry-run 单次停止
- 多任务顺序成功
- ready-gate timeout 停止
- 默认失败即停
- `--continue-on-failure`

**没有**覆盖：

- 两台机器人
- assignment uniqueness
- heartbeat timeout
- requeue / reassignment
- resource lock
- pickup → dropoff FSM

稳定基线必须继续保护的文件：

```text
launch/navigation.launch.py
config/nav2_params.yaml
maps/warehouse.yaml
launch/slam.launch.py
config/laser_filters.yaml
config/slam_toolbox.yaml
amr_warehouse_sim/odom_tf_node.py
worlds/warehouse_full.world
models/my_robot/model.sdf
```

`AGENTS.md` 当前仍写着“不要引入多车协同”。Stage 1 开始前需要把协作约束更新为：**允许新增独立 Fleet 模块，但禁止改写 Nav2 稳定基线**。这是文档门禁，不是本轮实现。

---

## 4. 工业分层映射

目标分层：

```text
WMS
 ↓   有什么业务任务需要完成
EMS / Fleet Dispatcher
 ↓   哪台机器人去做、何时做、异常如何回收
Robot Executor
 ↓   把已分配任务变成 NavigateToPose
Nav2
 ↓   规划与控制
AMR
```

本仓库现状映射：

| 工业角色 | 本仓库当前对应物 | 匹配程度 | 后续处理 |
| --- | --- | --- | --- |
| WMS | Mock WMS CLI / FastAPI / SQLite `tasks` | 部分匹配：能创建业务意图，但只有单点 goal | **保留并扩展字段**，不要让它选机器人 |
| EMS / Fleet Manager | 不存在。FIFO `get_next_pending_task()` 是假调度 | 缺失 | **新增独立模块** |
| Robot Executor | `mock_wms_executor` + `RosNav2Runtime` | 部分匹配：会发 NavigateToPose，但绑定全局单栈 | 抽象为 per-robot context |
| Nav2 | `navigation.launch.py` + `nav2_params.yaml` | 匹配，且已是稳定基线 | **保留，不重写规划器** |
| AMR | Gazebo `my_robot` | 匹配单车 | Stage 6 再考虑第二台，且必须 opt-in |
| Traffic / Resource Manager | 不存在 | 缺失 | Stage 5 只做 1–2 个逻辑锁 |

为什么 WMS 不应直接控制机器人：

- WMS 知道的是货从哪来、到哪去、优先级是什么。
- 它不知道哪台车电量够、哪台车离 pickup 近、哪台车已经在窄通道里、哪台车心跳丢了。
- 当前 executor 直接消费 WMS pending 队列，等于把 EMS 省略了。单车时看不出来；两台车时会把所有任务都塞给同一条 `/navigate_to_pose`。

为什么 EMS 必须存在：

- 维护 robot registry（谁在、谁闲、谁坏）。
- 做 assignment（哪个 IDLE 机器人接哪张单）。
- 做 recovery 的第一层（心跳超时后释放任务），而不是让 WMS 去懂 Nav2。
- 做很薄的资源占用（站点 / 窄通道），避免两台车同时冲进同一逻辑资源。

EMS 与 Nav2 的边界：

- EMS 不发 `/cmd_vel`，不算全局路径，不实现 CBS / MAPF。
- Nav2 不知道任务优先级、不维护 fleet 心跳、不决定哪台车接单。
- Robot Executor 是两者之间的适配器：吃 assigned task，调用该机器人自己的 NavigateToPose。

---

## 5. 哪些组件应该保留

按“不要推翻现有架构”原则，下列内容应原样保留为单机器人 baseline：

### 5.1 必须冻结的导航 / 仿真基线

- `launch/navigation.launch.py`
- `launch/simulation.launch.py`
- `launch/slam.launch.py`
- `config/nav2_params.yaml`
- `config/laser_filters.yaml`
- `config/slam_toolbox.yaml`
- `maps/warehouse.yaml` + `maps/warehouse_slam.pgm`
- `worlds/warehouse_full.world` 的默认单车 include
- `models/my_robot/model.sdf`
- `amr_warehouse_sim/odom_tf_node.py`
- `amr_warehouse_sim/initial_pose_publisher.py`
- `rviz/nav2.rviz`

单机器人模式必须继续能跑：

```bash
ros2 launch amr_warehouse_sim navigation.launch.py
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone
ros2 run amr_warehouse_sim create_mock_task --target station_a
ros2 run amr_warehouse_sim mock_wms_executor --execute
```

### 5.2 必须保留的 Mock WMS 能力

- SQLite 本地任务表
- `init / create / list` CLI
- FastAPI `/health` 与 `/tasks*`
- `config/task_points.yaml` 作为站点字典
- executor 的 ready gate 思想
- `ExecutorRuntime` + `FakeRuntime` 测试缝
- 现有 63 个 pytest 作为 regression gate（Scenario H）

### 5.3 可以参考、但不要接回主线的内容

- `future_extensions/wms_integration/task_manager/wms_dispatcher.py`：这是 JSON waypoint 顺序执行器，文件名有 dispatcher，实际不是 EMS。
- `archive/nav2_legacy/`：旧 spawn / 旧 TF，禁止接回。
- `future_extensions/wms_integration/config/waypoints.json`：历史点位，主线点位仍是 `task_points.yaml`。

---

## 6. 哪些组件需要抽象

这些地方今天把“唯一一台机器人”写进了实现细节，后续需要变成接口，而不是先复制文件。

| 当前实现 | 单机器人假设 | 建议抽象 |
| --- | --- | --- |
| `get_next_pending_task()` | 全局只有一个消费者 | WMS 只提供 pending 业务任务；EMS 负责 claim |
| `tasks.status` | 同时表示业务状态和执行状态 | 拆成 WMS task state / assignment state / robot execution state |
| `RosNav2Runtime` | 一个全局 action client | `RobotExecutionContext`：`robot_id` + action name + ready gate names |
| `REQUIRED_LIFECYCLE_NODES` | `/map_server` 等绝对名 | 按 robot namespace 生成，或 Stage 1–5 用 simulated gate |
| `DEFAULT_ACTION_NAME = '/navigate_to_pose'` | 全局唯一 action | `/{robot_id}/navigate_to_pose`，单车模式保持旧默认 |
| HTTP `/tasks` PATCH | 外部可任意改状态 | WMS 状态仍可回写，但 assignment 不走这条通用 PATCH 冒充调度 |
| `mock_wms_task_runner` | 一条队列一台车 | 保留为单车回归入口；Fleet 另做 dispatcher loop |
| `current_station` 缺失 | 默认车在 `start_zone` | registry 显式保存 station 或 last known pose abstraction |

推荐的新模块边界（Stage 1 才开始建，本轮不建）：

```text
amr_warehouse_sim/fleet/
    registry.py          robot_id, state, heartbeat, current_task_id
    dispatcher.py        pending -> assignment
    assignment.py        assigned_robot_id, cost, reason
    heartbeat.py         last_seen, timeout -> OFFLINE
    resources.py         FREE / OWNED(robot_id)
    logging.py           structured events
```

Mock WMS 继续留在：

```text
amr_warehouse_sim/mock_wms_*.py
```

不要出现 `mock_wms_dispatcher.py` 这种把 EMS 藏进 WMS 文件名的设计。

---

## 7. 单机器人假设存在在哪里

按风险从高到低：

### 7.1 仿真与 TF（Stage 6 高风险）

| 位置 | 假设 |
| --- | --- |
| `worlds/warehouse_full.world` | 只 include 一台 `my_robot`，出生在 `(0,0,0)` |
| `models/my_robot/model.sdf` | DiffDrive / lidar 发布全局 `/cmd_vel` `/odom` `/scan`；`child_frame_id=base_link` |
| `launch/simulation.launch.py` | 全局 bridge；lidar TF 写死 `my_robot/lidar_link/lidar` |
| `amr_warehouse_sim/odom_tf_node.py` | 订阅 `/odom`，发布 `odom -> base_link` |
| `models/my_robot_visual.urdf` | 单一 `base_link` RobotModel |

### 7.2 Nav2 栈（Stage 6 高风险）

| 位置 | 假设 |
| --- | --- |
| `launch/navigation.launch.py` | 无 namespace，include 一份 bringup |
| `config/nav2_params.yaml` | `map / odom / base_link`，`/scan_filtered`，`/odom` |
| `test/integration/test_navigation_pipeline_contract.py` | 把上述全局契约锁死 |
| AMCL `always_reset_initial_pose: true` | 面向单车 initial pose 注入 |

### 7.3 任务层（Stage 1–3 必须先拆）

| 位置 | 假设 |
| --- | --- |
| `tasks` 表 | 没有 `robot_id` |
| `get_next_pending_task()` | 全世界只有一个执行者 |
| `mock_wms_executor.RosNav2Runtime` | 一个 node、一个 action client |
| `mock_wms_task_runner` | 顺序排空同一队列 |
| HTTP API | 只有 task 资源 |
| `docs/designs/mock_wms_executor_design.md` | 明确写出“不做多机器人” |

### 7.4 文档与协作约束

| 位置 | 假设 |
| --- | --- |
| `README.md` | “当前不是多机器人调度系统” |
| `docs/design.md` / `docs/roadmap.md` | 多机器人列为未来项，未进主线 |
| `AGENTS.md` | 禁止引入多车协同、禁止重构 world / model |

这些约束在 Stage 0 是正确的保护机制。进入 Stage 1 时，应改成“允许新增独立 Fleet 层，禁止破坏单车 Nav2 基线”，而不是直接解禁改 launch。

---

## 8. 多机器人化需要改哪些位置

分两档：**调度层可改** 与 **仿真 / Nav2 层暂缓**。

### 8.1 Stage 1–5 需要改（低 / 中风险）

新增，尽量不改现有主线行为：

```text
docs/fleet/*                         设计文档
amr_warehouse_sim/fleet/*            新模块
test/integration/test_fleet_*.py     Scenario A–G
SQLite 新表或同库新 schema           robots / assignments / resources
FastAPI 新路由                       /robots /fleet/assignments /heartbeat
```

对现有 Mock WMS 的最小扩展，而不是重做：

```text
tasks 表增加可选业务字段
  pickup_name, dropoff_name, priority
  旧的 target_name 单点任务继续可用（兼容单车 baseline）

不要删除 pending/running/succeeded/failed/canceled
不要让 /tasks 承担 assignment
```

executor 的演进方式：

```text
保留 mock_wms_executor 作为单车入口（Scenario H）
新增 per-robot executor adapter，由 Fleet 调用
禁止让 Fleet Dispatcher 自己发 /cmd_vel
```

### 8.2 Stage 6 才考虑改（高风险）

若要真实：

```text
/robot_01/...
/robot_02/...
```

至少要处理：

| 主题 | 当前 | 双车时必须变成 |
| --- | --- | --- |
| Gazebo model name | `my_robot` | `robot_01` / `robot_02` |
| spawn | world include 一台 | opt-in spawn 两台，不同 pose |
| `/cmd_vel` `/odom` `/scan` | 全局 | `/robot_xx/cmd_vel` 等 |
| TF | `odom` `base_link` | `robot_xx/odom` `robot_xx/base_link`，或 prefix |
| lidar frame | `my_robot/lidar_link/lidar` | 每台唯一 frame |
| bridge | 一组 parameter_bridge | 每台一组 remap |
| `odom_tf_node` | 硬编码 `/odom` | 参数化 robot_id |
| Nav2 bringup | 一份、无 namespace | 两份 namespaced bringup |
| lifecycle / action | `/bt_navigator` `/navigate_to_pose` | `/robot_xx/bt_navigator` `/robot_xx/navigate_to_pose` |
| map | 一份 `/map` | 可共享 map_server，但 localization / planner 必须分车 |
| initial pose | `/initialpose` | `/robot_xx/initialpose` |
| laser_filters | 全局 `/scan_filtered` | 每车一条 filter chain |
| RViz | 单 RobotModel | 两台或分视图；不阻塞调度层 |

共享 `/map` 是合理的：仓库地图只有一份。  
共享 `map -> odom` 和 `base_link` **不合理**：这是 Stage 6 的核心 blocker。

### 8.3 明确不改

- 不自研全局规划器
- 不引入 CBS / MAPF / MARL
- 不把 `future_extensions/` 旧 WMS runner 接回主线
- 不新建 GitHub 仓库
- 不引入 Redis / Kafka / Kubernetes / 微服务拆分
- 不把 Mock WMS 扩成订单 / 库存 / 权限系统

---

## 9. 哪些改动风险较高

### 9.1 高风险：真实双 Nav2 / 双 Gazebo 机器人

原因：

- 当前稳定基线是靠全局话题和全局 TF 打磨出来的。
- `test_navigation_pipeline_contract.py` 会锁定这些字符串。
- Nav2 Jazzy namespacing 还涉及 `RewrittenYaml`、lifecycle 节点名、BT 内 action 名、costmap frame。
- 两台差速车共用 `base_link` 会直接破坏 TF 树。
- 货架通道较窄，两台真车即使调度正确，Nav2 local costmap 仍可能互相把对方当障碍；这已经超出“最小 EMS”而进入 traffic。

推荐：Stage 6 先出 blocker 清单和 opt-in 方案；若实施成本会破坏单车 baseline，就停在 simulated execution context。这不是失败，这是正确的工程判断。

### 9.2 高风险：把 Fleet 状态写进现有 `tasks.status`

如果把 `ASSIGNED / NAVIGATING_TO_PICKUP / WAITING` 塞进当前 WMS status：

- 现有 executor / HTTP / CLI / Dashboard 契约会碎。
- 三个状态机将无法讲解。
- Scenario H 会红。

必须拆开：

```text
WMS task state        pending / assigned / in_progress / succeeded / failed / canceled / requeued
Fleet assignment      unassigned / assigned / executing / released
Robot execution       IDLE / ASSIGNED / BUSY / OFFLINE / ERROR
                      以及搬运子状态 NAVIGATING_TO_PICKUP / PICKUP / ...
```

第一版可以用独立表或独立字段，而不是覆盖旧枚举。旧单点任务仍只用 `pending / running / succeeded / failed / canceled`。

### 9.3 中风险：改 executor 主路径

`mock_wms_executor.py` 已有 SQLite 与 HTTP 两条路径，测试面大。  
最小做法：新增 Fleet 调用的 adapter，让旧 CLI 默认行为不变。

HTTP dry-run 会把任务写成 `succeeded`。如果 Dispatcher 把 HTTP dry-run 当真实完成，重分配和回归都会失真。Stage 2/3 必须把 “simulated execution” 做成显式的 execution context，而不是复用这条会写终态的 HTTP dry-run。

### 9.4 中风险：改 `task_points.yaml` / 导航参数来迁就调度

不需要。静态 station 距离已经够第一版 cost。  
不要为了欧氏距离去改 AMCL、costmap 或 footprint。

### 9.5 低风险：新增 Fleet 模块 + pytest

这是本轮主路径。`FakeRuntime` 已经证明这种测试风格可行。

### 9.6 过程风险：`AGENTS.md` 仍禁止多车协同

若不更新协作约束，后续 agent / 开发者可能拒绝新增 Fleet。  
应在 Stage 1 开始时用一句话放宽：**允许 `amr_warehouse_sim/fleet/` 与 `docs/fleet/`，禁止改 Nav2 基线文件**。Stage 0 只记录，不改。

---

## 10. 推荐的最小实现顺序

继续按用户给定的 Stage 推进。每个 Stage 有进入条件、交付物和 **gate**。看不到“可以顺便做”就停。

### Stage 0 — Architecture Audit（本文件）

状态：**本轮完成**。

Gate：

- [x] 审计了 task schema / SQLite / API / executor / runner / task points / Nav2 / Gazebo / robot state / tests
- [x] 明确保留、抽象、单车假设、高风险项
- [x] 未改业务代码，未开始 Stage 1

### Stage 1 — Robot Registry

目标：先有机器人对象，再谈调度。

建议：

- 内存或 SQLite `robots` 表均可；优先可单测的纯 Python 对象 + 可选持久化。
- 预置 `robot_01`、`robot_02`。
- 字段：`robot_id`、`state`、`current_task_id`、`current_station`、`last_heartbeat`、`battery`。
- 状态：`IDLE / ASSIGNED / BUSY / OFFLINE / ERROR`，写明合法转移。
- 约束：同一 robot 不能有两个 active task；`OFFLINE` 不能接任务。
- 用 **SimulatedRobotContext**，不要启动两套 Nav2。

Gate：

- 状态机单测通过
- 双 active task 被拒绝
- 现有 63 tests 仍通过
- 未修改 `navigation.launch.py` / `nav2_params.yaml`

### Stage 2 — Fleet Dispatcher

目标：把 FIFO 替换成“选一台 IDLE 机器人”。

候选：

```text
state == IDLE
AND heartbeat valid
AND current_task_id is empty
```

第一版 cost：

```text
cost = distance(current_station, pickup_station)
     + workload_penalty          # 第一版可恒为 0
     + optional_priority_penalty
```

距离来自 `task_points.yaml` 静态坐标，不读 TF。

记录：`assigned_robot_id`、`assigned_at`、`dispatch_reason`、`cost`。

Gate：Scenario A / B / C / D 的 pytest 通过。Dispatcher 不调用 `/cmd_vel`。

### Stage 3 — Pickup → Dropoff FSM

把“去一个点”升级为最小搬运流程。WMS 负责任务是什么，Executor 负责怎么走点。

```text
PENDING
  → ASSIGNED
  → NAVIGATING_TO_PICKUP
  → PICKUP                 # sleep / ack 即可
  → NAVIGATING_TO_DROPOFF
  → DROPOFF                # sleep / ack 即可
  → SUCCEEDED
异常：FAILED / CANCELED / REQUEUED
```

三个状态必须分开存储。  
旧的单点 `target_name` 任务应仍能在单车 executor 里跑，作为 regression。

Gate：搬运 FSM 单测通过；单点 baseline 测试不红。

### Stage 4 — Heartbeat / Offline / Reassignment

```text
robot_01 last_seen timeout
  → OFFLINE
  → 若任务尚未进入不可逆阶段（建议：尚未完成 PICKUP）
      释放 assignment
      任务 REQUEUED
      dispatcher 分给 robot_02
```

必须在文档写明：

> demo-level reassignment ≠ production recovery semantics

生产系统还要处理：货物是否已在车上、站点是否已占用、Nav2 goal 是否已发出且机器人正在运动中、人工接管、充电与锁定。本 demo 只覆盖“分配后、取货前失联”。

Gate：Scenario E 通过。

### Stage 5 — Resource Lock

只选 1–2 个逻辑资源，例如：

```text
pickup_station_a
narrow_aisle_1
```

能力：ownership / acquire / release / timeout / 等待。  
建议加一条最简单的防死锁规则：按资源名排序加锁（lock ordering）。  
不宣称 collision-free 或多机规划。

Gate：Scenario F / G 通过。

### Stage 6 — Actual Multi-Robot Gazebo / Nav2

仅当 Stage 1–5 测试稳定后启动。  
先写 `MULTI_ROBOT_DEMO.md` 的 blocker 与 opt-in 方案，再决定是否改 launch。

若发现必须大改 `navigation.launch.py` 才能跑通两套 Nav2：

- **不要强行一次完成**
- 保持 `single robot mode` 为默认
- 多机器人 launch 必须新文件，例如未来的 `launch/fleet_simulation.launch.py`，不得替换现有入口

当前已知 Stage 6 blocker（预告，本轮不修）：

1. world 只 include 一台车
2. SDF 全局 `/cmd_vel` `/odom` `/scan`
3. 全局 `base_link` / `odom` TF
4. 无 namespace 的 Nav2 bringup
5. executor 绝对 action 名
6. 导航契约测试锁死全局字符串
7. `AGENTS.md` 仍保护这些文件

### Stage 7 — Docs / Demo / Regression

补齐：

```text
docs/fleet/EMS_FLEET_DESIGN.md
docs/fleet/TASK_LIFECYCLE.md
docs/fleet/ROBOT_STATE_MACHINE.md
docs/fleet/RESOURCE_LOCKING.md
docs/fleet/MULTI_ROBOT_DEMO.md
```

再更新 README。口径必须是最小 Fleet / EMS 学习层，不是生产级调度平台。

Scenario H：现有 pytest 全绿，单车 CLI 路径仍可用。

---

## 11. 建议的数据边界（供后续设计，本轮不实施）

```text
WMS Task
  id
  pickup / dropoff 或兼容 target_name
  priority
  wms_status
  不包含 robot 运行时状态

Assignment
  task_id
  robot_id
  assigned_at
  cost
  reason
  assignment_status

Robot
  robot_id
  state
  current_task_id
  current_station
  last_heartbeat
  battery

Resource
  resource_id
  owner_robot_id | FREE
  acquired_at
  timeout
```

API 建议：

```text
保留
  GET/POST /tasks
  GET /tasks/{id}
  PATCH /tasks/{id}/status     # 仍表示 WMS 状态，不表示 fleet claim

新增
  GET  /robots
  GET  /robots/{robot_id}
  POST /robots/{robot_id}/heartbeat
  GET  /fleet/assignments
  GET  /fleet/tasks            # 若只是带 assignment 视图，避免再造一套 WMS 任务
```

若 `GET /tasks` 已够列出业务任务，`GET /fleet/tasks` 只应返回“调度视图”（谁被分到哪台车），不要复制一套 task CRUD。

结构化日志事件（后续实现，不引入大型 observability stack）：

```text
TASK_CREATED
TASK_ASSIGNED
ROBOT_BUSY
NAV_STARTED
NAV_SUCCEEDED
RESOURCE_ACQUIRED
RESOURCE_RELEASED
HEARTBEAT_TIMEOUT
ROBOT_OFFLINE
TASK_REQUEUED
TASK_REASSIGNED
TASK_SUCCEEDED
```

每条至少包含：`timestamp`、`event`、`task_id`、`robot_id`、`reason`。

---

## 12. 与学习目标的对照

当前 HEAD 已经能部分回答、但还不完整：

| 问题 | 当前 HEAD 能回答什么 | Fleet 层还缺什么 |
| --- | --- | --- |
| WMS 为什么不直接控制机器人？ | executor 已经不发 `/cmd_vel`，只发 NavigateToPose | WMS 仍直接 FIFO 喂给唯一执行器，等于没有 EMS |
| EMS 为什么存在？ | 文档承认缺失 | 需要 registry + assignment + recovery |
| 搬运任务如何从 WMS 变成机器人任务？ | 现在是单点 `target_name` → 一个 goal | 需要 pickup/dropoff 两段执行 |
| 如何选择执行者？ | 不选择，谁跑 executor 谁执行 | IDLE + heartbeat + cost |
| busy / idle / offline 如何影响调度？ | 只有 task running | 需要 robot state machine |
| 失联以后任务怎么办？ | 无 | heartbeat timeout + REQUEUED |
| 为什么需要 resource ownership？ | 无 | 站点 / 窄通道逻辑锁 |
| EMS 与 Nav2 边界？ | executor 已接近 Robot Executor | Dispatcher 还没从 executor 里拆出来 |
| 商业平台还多什么？ | 当前文档已承认不是生产系统 | 地图交通管制、电池策略、多楼层、权限、死锁检测、真实恢复语义、可观测性、多车避让 |

商业 AMR 调度平台相对这个 demo 通常还多：

- 实时位姿与交通图，而不只是 station 名字
- 路权 / 交管 / 速度区，而不只是一把资源锁
- 充电、停车、维保、模式切换
- 与真实 WMS/ERP 的订单、库存、容器、波次
- 生产级失败分类：导航失败、定位丢失、货物异常、人工介入
- 多车 collision avoidance 或空间预留，而不是 costmap 里互相当障碍碰运气
- HA、审计、权限、多仓、多地图版本

本项目做到 Stage 5，目标是**能讲清楚这些为什么存在**，而不是实现它们。

---

## 13. Stage 0 Gate

| 检查项 | 结果 |
| --- | --- |
| 只读审计，未大规模改代码 | 通过。本轮只新增本文件 |
| 未开始 Stage 1 实现 | 通过 |
| 单车稳定基线文件未改 | 通过 |
| 明确后续不得把 EMS 塞进 Mock WMS | 通过，见第 4–6 节 |
| 明确 Stage 6 为 opt-in 且高风险 | 通过，见第 8–9 节 |
| 现有 pytest 仍是 regression 锚点 | 通过，63 collected |

**是否满足进入 Stage 1：** 是。

进入 Stage 1 时建议先做、且只做：

1. 在 `AGENTS.md` / `docs/design.md` 增加一句：允许独立 Fleet 模块，禁止改 Nav2 基线。
2. 实现 Robot Registry + 状态机 + 单测。
3. 用 simulated robot，不复制 launch。

进入 Stage 1 时不要做：

- 第二台 Gazebo 车
- 第二套 Nav2
- 改 `config/nav2_params.yaml`
- 重写 FastAPI
- 把 pickup/dropoff、heartbeat、resource lock 一并做掉

---

## 14. 本轮未解决问题（刻意留下）

- Robot Registry 尚未实现
- Dispatcher / cost 尚未实现
- 搬运 FSM 尚未实现
- Heartbeat / reassignment 尚未实现
- Resource lock 尚未实现
- 双机器人 Gazebo / Nav2 尚未证明可行
- HTTP dry-run 与 SQLite dry-run 语义不一致，尚未统一
- `mock_wms_task_runner` 无 HTTP 模式
- `tasks.status` 无转移校验
- Dashboard / 外部仓库如何展示 fleet 资源，不在本仓库本轮范围

这些都不是 Stage 0 的缺陷，而是后续 Stage 的工作项。
