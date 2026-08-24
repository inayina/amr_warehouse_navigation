# AMR 项目面试复习与规模化并发开发指南

最后更新：`2026-08-24`

## 1. 文档定位与证据边界

本文用于两个场景：

1. 面试前复习 ROS 2、机器人系统集成、AMR、巡检机器人和 SDK 二次开发相关项目内容。
2. 后续把当前单车 / demo 系统扩展为多 executor、多机器人或常驻服务时，识别并解决并发、一致性和恢复问题。

代码事实审计基线：

```text
branch: main
HEAD: d8ac515 Add inspection validation for mock pipeline and Nav2 executor
audit-time worktree: clean
```

审计时测试结果：

```text
.venv/bin/python -m pytest test -q
169 passed
```

系统 Python 缺少 FastAPI 时结果为 `162 passed, 7 skipped`；7 个 skip 都是 HTTP API 测试的依赖缺失，不应误报为功能失败。

证据使用规则：

- 只有当前源码、配置、测试和已保存运行报告支持的结论才写成“已实现”。
- `archive/`、`future_extensions/`、设计文档和 TODO 不算当前实现。
- pytest 大部分属于 contract / fake / simulated 验证，不等于本轮启动 Gazebo 做实时验收。
- 历史 fresh-session 报告证明当时的仿真结果，不等于真机验收或生产可用。
- 本文审计完成后若继续新增巡检代码，应重新审计后再更新本文。

## 2. 一句话项目定位

> 这是一个以单车 Gazebo / Nav2 为真实主线、以 Mock WMS 串起任务状态闭环，并通过纯 Python 模型验证 Fleet 基础语义、通过 Mock 传感链验证巡检流程的 ROS 2 系统集成项目；它不是完整 WMS、生产级 Fleet、真机控制系统或功能安全系统。

## 3. 实现成熟度矩阵

| 子系统 | 当前结论 | 不能夸大的边界 |
| --- | --- | --- |
| Gazebo 仓库和差速 AMR | 已实现，仿真限定 | 单机器人 `my_robot` |
| LaserScan、里程计、TF | 已实现，仿真限定 | `/scan`、`/odom` 来自 Gazebo bridge |
| SLAM Toolbox 建图 | 已实现，仿真限定 | 已保存 `maps/warehouse.yaml` |
| Nav2 定位、规划、控制 | 已实现，仿真限定 | 单车、全局 topic / frame |
| 固定点导航 | 已实现，有历史运行证据 | 候选业务点，不是实仓最终坐标 |
| Mock WMS SQLite / CLI | 已实现，Mock | 单点任务和粗粒度五态 |
| Mock WMS HTTP REST | 已实现，Mock | 无权限、订单、WebSocket、MQTT |
| WMS 到 Nav2 executor | 已实现，单车仿真 | 使用 `NavigateToPose` |
| Fleet Registry / Dispatcher | 已实现为纯 Python demo | 未接 Gazebo 多车 |
| pickup 到 dropoff FSM | 已实现为模拟状态机 | PICKUP / DROPOFF 是模拟 ack |
| Heartbeat / OFFLINE / requeue | 已实现为显式函数调用 | 不是常驻 watchdog |
| Resource Lock | 已实现为逻辑 demo | 未接导航路径或交通管制 |
| Fleet 双车运行 | 未实现 | Stage 6 deferred |
| 电池调度和充电 | 未实现 | `battery` 字段未进入 eligibility |
| E-stop / 安全 PLC / 硬件 watchdog | 未实现 | Collision Monitor 默认关闭 |
| 巡检数据链 | 部分实现 | Nav2 是仿真真链路；到点、稳定、采集为 Mock |
| Unitree / Deep Robotics / Agibot | state-only 实验 | 只更新 heartbeat，不发运动命令 |
| Dashboard | 外部仓库 | 本仓库只提供 HTTP 数据入口 |
| WebSocket / MQTT | 未实现 | 不得说已支持实时推送 |

## 4. 30 秒、1 分钟和 3 分钟口述

### 4.1 30 秒版本

> 我做的是一个 ROS 2 Jazzy 的仓储 AMR 仿真导航项目。底层用 Gazebo 模拟差速机器人、激光和里程计，中间用 TF、AMCL 和 Nav2 完成定位与点到点导航，上层用 SQLite 和 FastAPI 做了一个最小 Mock WMS，再由 executor 把任务转换成 `NavigateToPose` Action 并回写状态。项目还用纯 Python 测试了 Fleet 注册、分配、心跳重分配和资源锁，但真实多车 Gazebo 尚未实现。

### 4.2 1 分钟版本

> 这个项目解决的是“上层任务怎样可靠落到机器人导航执行，并把结果返回”的最小闭环。Gazebo 产生 `/scan`、`/odom` 和 `/clock`，经过激光过滤、TF 和 AMCL 建立 `map -> odom -> base_link`。Nav2 使用静态地图、NavFn 全局规划和 MPPI 局部控制，最终通过 `/cmd_vel` 驱动 Gazebo 差速模型。上层不是完整 WMS，而是 SQLite、CLI 和 FastAPI 组成的 Mock 任务入口。executor 会先检查五个 lifecycle node、`map -> odom` 和 `/navigate_to_pose`，只有 ready 后才发 goal，并把 Action 结果写回任务状态。Fleet 部分目前是独立纯 Python 验证，还没有接双车 Nav2。

### 4.3 3 分钟版本

> 我把项目分为五层。第一层是 Gazebo 仿真设备层，SDF 中有差速驱动和 GPU LiDAR，ROS-Gazebo bridge 把 `/cmd_vel`、`/odom`、`/scan` 和 `/clock` 接到 ROS 2。
>
> 第二层是机器人基础能力。`odom_tf_node` 根据 `/odom` 发布 `odom -> base_link`，静态 TF 描述 LiDAR 安装位置，激光经过 range 和 median filter。建图模式用 SLAM Toolbox 输出 `/map`；导航模式加载保存地图，由 AMCL 输出 `map -> odom`。
>
> 第三层是 Nav2。全局规划器使用 NavFn 加 A*，局部控制使用 MPPI，局部和全局 costmap 都消费 `/scan_filtered`，再经过 velocity smoother 输出控制命令。Collision Monitor 虽然有配置，但稳定基线中是 disabled，所以不能说已完成安全停车验收。
>
> 第四层是任务执行。Mock WMS 只保存单目标任务。executor 先通过 lifecycle service、TF 和 Action server 做 ready gate，再发送 `NavigateToPose`。Action 成功或失败后，把 `running / succeeded / failed` 和 reason 写回 SQLite 或 HTTP。这里是同步串行消费，不是并发调度服务。
>
> 第五层是扩展验证。Fleet 用纯 Python 建模 Registry、Dispatcher、三套状态机、heartbeat 和 resource lock；默认执行上下文是 `SimulatedRobotContext`，所以真实双车仍未完成。巡检 P0-3 复用了仿真 Nav2 Action，但 arrival、stabilization 和 acquisition 是 Mock，主要验证导航成功与巡检质量、finding 不能混为一谈。

## 5. 当前真实架构

```text
外部 Robot Ops Dashboard（不在本仓库）
                    |
                 HTTP REST
                    v
Mock WMS API / CLI -----> SQLite mock_wms.db
                              |
                              v
              mock_wms_executor / task_runner
              - lifecycle ready checks
              - map -> odom check
              - NavigateToPose server check
                              |
                    NavigateToPose Action
                              v
Nav2: map_server -> AMCL -> BT Navigator
                   planner -> controller -> smoother
                              |
                    cmd_vel_nav / cmd_vel
                              v
Gazebo DiffDrive <----- ros_gz_bridge
      |
      +---- /odom ----> odom_tf_node ----> odom -> base_link
      |
      +---- /scan ----> laser_filters ---> /scan_filtered
                                           |
                                           +-> AMCL / costmap / SLAM
```

Fleet 当前是旁路验证层：

```text
Mock WMS row
     |
DispatchTask
     v
FleetDispatcher ------> RobotRegistry
     |                  IDLE / ASSIGNED / BUSY / OFFLINE / ERROR
     v
HaulTaskController
     |
RobotExecutionContext
     |
SimulatedRobotContext
     X
当前没有连接 per-robot Nav2 或双车 Gazebo
```

巡检 P0-3 链路：

```text
固定点位
-> RosNav2Runtime / NavigateToPose
-> Mock arrival acceptance
-> Mock stabilization
-> Mock temperature acquisition
-> freshness / completeness quality gate
-> versioned threshold rule
-> immutable local JSON + SHA-256
-> inspection report
```

## 6. 模块和通信清单

### 6.1 自定义 ROS 2 Node

| Node | 代码 | 责任 |
| --- | --- | --- |
| `OdomTfPublisher` | `amr_warehouse_sim/odom_tf_node.py` | 订阅 `/odom`，发布 `odom -> base_link` |
| `InitialPosePublisher` | `amr_warehouse_sim/initial_pose_publisher.py` | 向 `/initialpose` 重复发布初始位姿 |
| `mock_wms_executor` 内部 Node | `amr_warehouse_sim/mock_wms_executor.py` | lifecycle client、TF listener、Action client |
| Unitree adapter node | `integrations/unitree/state_adapter.py` | 订阅 `/lowstate`，只更新 liveness |
| Deep Robotics adapter node | `integrations/deep_robotics/state_adapter.py` | 订阅 `/JOINTS_DATA`，只更新 liveness |

Fleet Registry、Dispatcher、HeartbeatMonitor 和 ResourceLockManager 是纯 Python 类，不是 ROS Node，也不是常驻服务。Agibot adapter 是 Python 父进程加 C++ probe 子进程。

### 6.2 Topic / Service / Action

| 类型 | 当前直接使用 | 说明 |
| --- | --- | --- |
| Topic | `/cmd_vel`、`/odom`、`/scan`、`/scan_filtered`、`/clock`、`/initialpose`、`/tf` | 连续传感、控制和坐标数据 |
| Vendor Topic | `/lowstate`、`/JOINTS_DATA` | state-only telemetry |
| Service | `/<lifecycle_node>/get_state` | executor 的 ready gate |
| Action | `/navigate_to_pose` | 长时间导航任务 |

本仓库没有自定义 ROS 2 Service server 或 Action server。

### 6.3 非 ROS 通信

- HTTP REST：FastAPI API 与 executor 的 `urllib` client。
- SQLite：Mock WMS task、Fleet robot、assignment 和 resource metadata。
- JSONL pipe：Agibot C++ probe 到 Python adapter。
- 当前主线没有 WebSocket、MQTT、自研 TCP / UDP 或 gRPC。

## 7. 一次任务如何执行

### 7.1 正常任务

```text
POST /tasks 或 create_mock_task
-> resolve_target_pose()
-> INSERT pending task
-> executor 读取最早 pending
-> 检查 5 个 lifecycle node
-> 检查 map -> odom
-> 检查 /navigate_to_pose server
-> task = running
-> send_goal_async()
-> Nav2 规划、控制和 recovery
-> Action SUCCEEDED
-> task = succeeded
-> status_reason = NavigateToPose result: SUCCEEDED
```

### 7.2 失败、通信中断和恢复

- 无效目标：任务写成 `failed`，不会发送 goal。
- ready gate 超时：任务保持 `pending`，记录 readiness 原因。
- goal rejected / ABORTED / CANCELED / timeout：任务写成 `failed`。
- HTTP 拉取失败：executor 返回错误，通常不改变任务。
- 导航成功但 HTTP writeback 失败：机器人事实与 WMS 状态可能不一致。
- executor 中途崩溃：可能留下 `running`；当前重启时只取 `pending`，没有 reconciliation。
- 当前 HTTP 没有 retry / backoff / circuit breaker。

### 7.3 取消边界

当前没有完整端到端取消链：

- HTTP API 可以 PATCH `canceled`，但运行中的 executor 不轮询该状态。
- canceled 可能被 executor 最终结果覆盖。
- Fleet `HaulTaskController.cancel()` 只属于模拟 FSM，且只允许 pickup 前。
- Fleet execution contract 没有 `cancel()`。
- 真正调用 Nav2 `cancel_goal_async()` 的路径只有导航等待超时，不是用户取消。

面试时应说：

> 当前实现了 canceled 状态和导航超时取消，但没有实现用户取消从 WMS 到 Nav2 再到安全停止确认的完整闭环。

### 7.4 机器人离线

只在 Fleet demo 层实现：

```text
HeartbeatMonitor.sweep()
-> heartbeat stale
-> HEARTBEAT_TIMEOUT
-> pickup 前：REQUEUED + release robot
-> robot OFFLINE
-> 显式调用 reassign_requeued()
```

pickup 后不自动重分配；当前没有救援、人工交接或 load recovery 流程。Vendor adapter 使用 `recover_offline=False`，因为一帧 telemetry 只能证明 transport alive，不能证明机器人可以安全接任务。

## 8. ROS 2 与 Nav2 面试要点

### 8.1 Topic、Service、Action

- Topic：连续流，适合 LaserScan、Odometry、Twist 和 TF。
- Service：短请求响应，适合 lifecycle state 查询。
- Action：长任务，适合导航 goal 的接受、结果和取消。

### 8.2 ROS 2 Executor 与项目 executor

- `mock_wms_executor` 是业务任务执行器。
- rclpy Executor 是 callback 调度机制。
- 当前没有自定义 `MultiThreadedExecutor`，主要使用默认单线程 `spin`、`spin_once` 和 `spin_until_future_complete`。
- 当前没有显式 Callback Group。

### 8.3 QoS 与 DDS

- 自定义 pub/sub 大多只传 queue depth 10 或 20。
- 没有系统设计 reliability、durability、deadline、lifespan 或 liveliness。
- map costmap 配置使用 transient local 订阅语义。
- 仓库通过 ROS 2 使用 RMW / DDS，但没有实现 DDS discovery、安全或跨网段方案。

### 8.4 TF

```text
map -> odom -> base_link -> my_robot/lidar_link/lidar
```

- `map -> odom`：AMCL 或 SLAM Toolbox。
- `odom -> base_link`：当前仿真由 `odom_tf_node` 根据 `/odom` 发布。
- LiDAR 外参：static transform publisher 和 robot description。

### 8.5 goal 到运动

```text
BT Navigator
-> planner_server / global costmap / NavFn A*
-> controller_server / local costmap / MPPI DiffDrive 20 Hz
-> velocity_smoother
-> collision_monitor node（当前 disabled）
-> /cmd_vel
-> ros_gz_bridge
-> Gazebo DiffDrive
```

关键事实：

- AMCL、local/global costmap 使用 `/scan_filtered`。
- footprint 约 `0.56 m x 0.42 m`。
- inflation radius 为 `0.40 m`。
- velocity smoother timeout 为 `1.0 s`，不能代替硬件 watchdog。
- Nav2 costmap 避障不等于安全认证避障。

## 9. Fleet 当前能力和 5 到 10 台扩展

### 9.1 已有

- Robot Registry 和五态 Robot FSM。
- fresh heartbeat eligibility。
- 静态站点欧氏距离 cost。
- Assignment record。
- pickup 到 dropoff FSM。
- pickup 前 requeue / reassign。
- 逻辑 resource acquire / release / FIFO wait / timeout。

### 9.2 未实现

- 双车 Gazebo / Nav2 runtime。
- per-robot namespace、TF、action 和 executor。
- WMS 到 Dispatcher 的常驻自动轮询。
- capability 和 battery scheduling。
- 基于真实路径和拥堵的 cost。
- traffic reservation / conflict resolution。
- Fleet HTTP API 和生产级恢复。

### 9.3 扩展需要增加

1. 每机器人 namespace、TF tree、Nav2 action 和 command owner。
2. 原子 task claim、assignment 唯一约束和 execution lease。
3. per-robot actor / queue，保证同一机器人串行执行命令。
4. capability、battery、fault、map version eligibility。
5. 路径成本和交通资源 reservation。
6. heartbeat、business availability、execution readiness、safety readiness 分层。
7. 重启恢复、状态对账、outbox 和幂等回写。
8. metrics、structured log、trace 和告警。

## 10. 仿真转实机与 SDK Adapter

### 10.1 尽量保持不变

- task contract。
- 业务、assignment、execution 状态分离。
- Fleet 领域模型。
- inspection observation / evidence / report。
- ready gate 和测试分层思想。

### 10.2 必须替换或标定

- Gazebo、SDF DiffDrive、GPU LiDAR 和 bridge。
- LiDAR / IMU / encoder / base driver。
- `/odom` 和 `odom -> base_link` 的唯一权威来源。
- URDF、外参、footprint、地图和 `use_sim_time`。
- 速度、加速度、controller 和 costmap 参数。
- command watchdog、E-stop、断连和 fault recovery。

### 10.3 当前 Adapter 缺口

已有 `ExecutorRuntime`、`RobotExecutionContext` 和三个 state-only vendor adapter，但两套 runtime 接口不兼容：Fleet 的 `navigate_to_pose()` 不接 pose/timeout，也没有 cancel、stop、execution ID、feedback 和 fault contract。

建议目标接口：

```text
RobotExecutionContext
- check_readiness()
- start_navigation(pose, execution_id, timeout)
- query_execution(execution_id)
- cancel_execution(execution_id)
- request_safe_stop(reason)
- close()
```

业务代码不能直接绑定厂商 SDK，否则 SDK 的 ABI、线程、错误码、单位和生命周期会污染 WMS / Fleet，并使仿真替换、故障隔离和多厂商接入变得困难。

## 11. 四足机器人 SDK 迁移口述

```text
WMS / Inspection Task
          |
Fleet / Task Manager
          |
Robot Execution Contract
       /             \
ROS 2 Nav2 Adapter   Vendor SDK Adapter
       |             |
仿真 / AMR          Unitree / Deep Robotics / Agibot
```

拿到陌生 SDK 的回答：

> 我会先固定官方版本和运行环境，审计通信方式、单位、坐标系、线程模型和停止语义；先运行只读 telemetry example，不发运动命令；再把有效 telemetry 映射成内部 liveness，但不推断业务 readiness；之后定义 process 或 ROS adapter，明确唯一 command owner、watchdog 和 E-stop；最后才在受控环境做低速命令 smoke，并通过统一 execution contract 接回 Fleet。

当前三家 vendor 都只验证了 state / liveness 边界，没有 command plane，不能说已经完成四足控制闭环。

## 12. 规模化开发必须解决的并发问题

本章是待实施路线图，不代表当前能力。

### 12.1 当前并发模型

- task runner 一次处理一条 pending task。
- rclpy 使用默认单线程 spin。
- Fleet 状态主要在进程内，没有 mutex。
- FastAPI async endpoint 内调用同步 SQLite。
- 数据库操作分别打开连接并提交。
- 没有 scheduler worker pool 或 per-robot actor。

这个模型适合 demo，但不能直接横向扩容。

### 12.2 P0：重复领取任务 race

当前可能发生：

```text
executor A: SELECT pending task 1
executor B: SELECT pending task 1
A: UPDATE running + send goal
B: UPDATE running + send goal
```

根因是 `get_next_pending_task()` 与 `update_task_status()` 不在同一原子 claim 中。

必须保证：

```text
同一 task / execution 同时最多有一个有效 owner。
同一 robot 同时最多有一个运动 command owner。
```

SQLite 单机过渡方案：

1. 增加 `execution_id`、`owner_id`、`lease_until`、`version`。
2. 使用事务和 compare-and-set。
3. 只有受影响行数为 1 才算 claim 成功。
4. 配置有限 `busy_timeout`，不要无限重试数据库锁。

示意：

```sql
BEGIN IMMEDIATE;

UPDATE tasks
SET status = 'running',
    owner_id = :owner_id,
    execution_id = :execution_id,
    lease_until = :lease_until,
    version = version + 1
WHERE id = :task_id
  AND status = 'pending'
  AND version = :expected_version;

-- rowcount == 1 才获得任务
COMMIT;
```

多进程或多机服务应迁移到支持 row lock 的数据库，使用 `FOR UPDATE SKIP LOCKED` 或等价机制。Python `threading.Lock` 不能保护跨进程数据。

### 12.3 P0：取消和完成竞态

```text
WMS cancel request
                 \ 同时 Nav2 SUCCEEDED
executor writes succeeded
```

必须定义：

- cancel 是 intent 还是终态。
- 谁拥有 Nav2 cancel。
- 是否等待机器人停止确认。
- success 和 cancel 同时出现时的优先级。
- 无法确认结果时进入什么状态。

建议状态：

```text
pending -> claimed -> executing
-> cancel_requested
-> canceled | succeeded | failed | outcome_unknown
```

owner 应通过 version / expected state 写最终结果，拒绝旧事件覆盖终态。

### 12.4 P0：导航成功但写回失败

不能只靠无限 HTTP retry。建议：

```text
Nav2 result
-> 同一事务保存 execution_result + outbox_event
-> projector 重试 WMS / Dashboard 投影
-> 消费端按 event_id 幂等
```

原则是先保存执行事实，再投影业务状态；远端管理面不可达不能抹掉机器人事实。

### 12.5 P0：进程崩溃与 lease 恢复

当前 executor 在写 `running` 后崩溃会留下永久 running。需要：

- execution lease 和 worker heartbeat。
- 启动时 reconciliation。
- 查询 robot / Nav2 当前 execution 的接口。
- 无法确认时进入 `outcome_unknown`，不能盲目重发。

| 状态 | lease / robot evidence | 恢复动作 |
| --- | --- | --- |
| running | lease valid + execution active | 继续观察 |
| running | expired + 明确未开始 | requeue |
| running | expired + 有成功证据 | 补写 succeeded |
| running | expired + 无法确认 | outcome_unknown / 人工处理 |

### 12.6 P0：同机器人并发命令

推荐 per-robot actor / serialized mailbox：

```text
Dispatcher workers
       |
       +-> robot_01 mailbox -> robot_01 actor -> one ActionClient
       +-> robot_02 mailbox -> robot_02 actor -> one ActionClient
```

每个 actor 串行处理 start、feedback、cancel、timeout、stop 和 completion。不能只依赖“Registry 看起来是 BUSY”，状态检查与赋值也必须原子化。

### 12.7 P1：FastAPI 和同步 SQLite 阻塞

`async def` 不会自动让同步 SQLite 变成非阻塞。可选方案：

- 使用同步 endpoint 和框架 thread pool。
- 使用有容量上限的 worker pool。
- 使用异步 driver，同时明确事务和连接池上限。
- 数据库迁移后配置 connection pool、deadline 和 statement timeout。

### 12.8 P1：Fleet 内存对象线程安全

Registry、Dispatcher、ResourceLockManager 都有 read-check-write 操作，多线程下可能两个请求同时通过检查。

建议：

1. 优先采用单 writer actor / event loop。
2. 单进程共享状态必须有清晰锁范围。
3. 跨进程唯一性由数据库事务和约束保证。
4. 内存 cache 只做 projection，不做跨进程唯一 authority。

### 12.9 P1：Assignment 约束

当前 `assignments` 表没有数据库级 active assignment 唯一约束；单进程 dict 不能保护多进程。

未来应保证：

- 一个 task 同时最多一个 active assignment。
- 一个 robot 同时最多一个 active assignment。
- reassign 使用新的 generation / assignment ID，保留历史。

可建立独立 `active_assignments` 表，让 `task_id`、`robot_id` 都有 UNIQUE 约束。

### 12.10 P1：Heartbeat 时间和状态竞态

需要区分：

- source timestamp。
- adapter receive timestamp。
- persist timestamp。
- monotonic liveness deadline。

同机 timeout 优先使用 monotonic clock；跨机 source time 保留为 provenance，但 liveness 以 server receive time 判断。heartbeat update 与 OFFLINE sweep 要通过 transaction / version 避免互相覆盖。

同时分开：

```text
transport liveness
business availability
execution readiness
safety readiness
```

### 12.11 P1：Resource lease 和 fencing token

当前 ResourceLockManager 的 wait queue 不持久化，构造时也没有恢复已有 owner；timeout 后旧 owner 仍可能继续执行。

生产型资源锁需要 lease + fencing token：

```text
robot_01 acquires aisle with token 41
lease expires
robot_02 acquires aisle with token 42
resource endpoint rejects all later token 41 commands
```

只有 lease、没有 fencing token，长暂停或网络分区后旧 owner 可能继续操作。

### 12.12 P1：死锁与物理占用

按 resource ID 排序只能避免一类 lock-order deadlock。还需处理：

- 部分 acquire 后失败的 rollback。
- hold-and-wait timeout。
- starvation 和 priority inversion。
- 机器人进入窄道后不能只按墙钟释放。
- 逻辑 owner 与物理位置不一致。

交通资源释放必须关联位置证据、占用传感器或受控 checkpoint。

### 12.13 P1：ROS callback 并发

接真实 telemetry 后要避免：

- callback 中直接做慢 SQLite / HTTP。
- feedback 与 cancel 同时修改 execution state。
- `MultiThreadedExecutor` 下共享 dict 无锁访问。
- shutdown 时 callback 访问已关闭 SDK。

建议 callback 只做校验和入队，由单 owner state machine 处理 execution；shutdown 顺序为停止 intake、drain/cancel、关闭 SDK、销毁 node。

### 12.14 P2：背压、幂等和观察性

必须定义 bounded queue、intake rate limit、telemetry aggregation 和 overload 策略。cancel、safe stop 等高优先级命令不能被普通 telemetry 或 report backlog 阻塞。

身份至少包括：

```text
task_id
assignment_id
execution_id
attempt_number
event_id
```

同一个 `event_id` 重复到达必须幂等，不能因 HTTP / MQTT retry 创建第二次机器人运动。

日志和指标至少关联：

- task / assignment / execution / robot / resource ID。
- state before / after。
- owner、lease generation、version。
- queue depth、claim conflict、heartbeat age。
- cancel latency、expired lease、outcome_unknown、outbox backlog。

## 13. 并发目标架构

```text
HTTP / WMS Intake
       |
Durable Task Store
atomic claim + version + lease
       |
Fleet Scheduler
capability / battery / resource eligibility
       |
Durable Assignment
       |
       +----------------------+
       |                      |
robot_01 actor            robot_02 actor
single command owner      single command owner
       |                      |
Robot Adapter / Nav2      Robot Adapter / Nav2
       |                      |
       +----------+-----------+
                  |
       Durable Execution Result
                  |
             Outbox / Projector
                  |
             WMS / Dashboard
```

E-stop、command watchdog 和 safe stop 必须位于 Robot Adapter / 底盘侧，不依赖远端 projection。

## 14. 并发开发路线图

### P0：增加第二个 executor 前

- 原子 task claim。
- `execution_id / owner_id / version / lease_until`。
- active assignment 唯一约束。
- per-robot single command owner。
- 端到端 cancel contract。
- running task restart reconciliation。
- durable execution result 和 outbox。

### P1：进入 2 到 5 台机器人前

- namespaced Nav2 和统一 RobotExecutionContext。
- heartbeat 原子迁移与 readiness 分层。
- resource lease + fencing token。
- 数据库迁移和连接池边界。
- structured event log 和 metrics。
- crash / network partition fault-injection tests。

### P2：进入 5 到 10 台和跨机器部署前

- capability / battery scheduler。
- traffic reservation 和物理占用证据。
- bounded queue 和 backpressure。
- leader election 或单 scheduler ownership。
- 高可用数据库、schema migration 和备份恢复。
- 安全域、权限、审计和现场运行手册。

## 15. 并发验收测试

1. 两个 executor 同时 claim 同一任务，只有一个成功。
2. 两个任务同时分配同一 robot，只有一个成功。
3. claim 后、发 goal 前崩溃。
4. 发 goal 后、写 running 前崩溃。
5. Nav2 成功后、写 result 前崩溃。
6. WMS cancel 与 Nav2 success 同时发生。
7. heartbeat 与 OFFLINE sweep 同时发生。
8. resource lease 过期时旧 owner 延迟恢复。
9. HTTP writeback 重复、乱序、长期不可达。
10. SQLite locked / 数据库事务超时。
11. executor 重启后 running task reconciliation。
12. command queue overload 时 cancel 仍可优先处理。
13. telemetry 洪峰不阻塞 safe stop。
14. 多资源部分获取失败可 rollback。
15. 旧 version 事件不能覆盖终态。

验收不能只看最终状态，还要确认是否发过重复 goal、是否曾出现两个 command owner、状态迁移是否可追踪，以及无法确认时是否进入 `outcome_unknown` 而非伪造结果。

## 16. 30 道项目面试题速记

### A. 项目介绍

1. **核心闭环是什么？** Mock WMS task -> ready gate -> NavigateToPose -> 状态回写。
2. **最有价值的点？** 把任务、执行、导航和证据边界组成可复核系统，不只是发一条 goal。

### B. 系统架构

3. **为什么 WMS 不发 `/cmd_vel`？** WMS 负责做什么，Nav2 / driver 负责怎么运动。
4. **最大架构断点？** Fleet 默认 Simulated context，未接 per-robot Nav2。

### C. ROS 2

5. **Topic / Service / Action 怎么选？** 连续流、短查询、长任务分别使用三者。
6. **是否实现 ROS 2 Executor？** 没有；项目 executor 是业务概念。

### D. 导航

7. **goal 到运动的链路？** BT -> planner -> MPPI -> smoother -> `/cmd_vel` -> Gazebo。
8. **map / odom / base_link？** 全局坐标、局部连续坐标、机器人本体。

### E. 并发

9. **多 executor 安全吗？** 不安全，pending read 和 running update 不原子。
10. **ResourceLock 是 mutex 吗？** 不是，是业务逻辑资源所有权 demo。

### F. 通信

11. **为什么上层 HTTP、底层 ROS 2？** 管理面跨语言，机器人 runtime 使用 typed middleware。
12. **为什么 Agibot 用子进程？** 隔离 C++ SDK ABI、生命周期和崩溃。

### G. 状态机

13. **为什么三套状态？** WMS、assignment、execution 的 owner 和语义不同。
14. **如何阻止非法跳转？** allow-list transition table；Mock WMS API 尚无迁移校验。

### H. Watchdog

15. **项目有 watchdog 吗？** 没有常驻或硬件 watchdog；只有 sweep 和软件 timeout。
16. **velocity timeout 能代替硬件 watchdog 吗？** 不能。

### I. 故障处理

17. **Nav2 not ready 怎么办？** 不发 goal，保持 pending 并记录原因。
18. **导航成功但 HTTP 失败？** 当前可能不一致；生产需 durable result + outbox。

### J. 仿真转实机

19. **第一批改什么？** driver、sensor、TF/time/map 和 safety，上层任务尽量不改。
20. **当前有完整 Adapter 吗？** 只有 seam 和 state-only adapter，没有 command/cancel/stop。

### K. SDK 二次开发

21. **陌生 SDK 如何开始？** 先官方环境和只读 telemetry，再 adapter，最后受控命令。
22. **三家 vendor 做到什么？** 统一 liveness 语义，没有 command plane。

### L. Fleet

23. **Dispatcher 如何选车？** IDLE + fresh heartbeat + no active task + 静态距离 cost。
24. **扩展到 10 台缺什么？** per-robot runtime、原子租约、交通、电池、恢复、观察性和安全。

### M. C++ / Python

25. **主项目是什么语言？** ament_python；C++ 仅独立 Agibot C++17 probe。
26. **Protocol 有什么用？** 解耦实现和测试；两套 execution protocol 仍需统一。

### N. Linux / CMake

27. **怎样构建？** `ament_python + setup.py + colcon --symlink-install`，根目录无 CMakeLists。
28. **运维脚本风险？** 大量 `pkill -f` 适合个人 demo，不适合生产 ownership。

### O. 系统设计

29. **如何做可靠取消？** cancel intent -> owner cancel Action -> stop confirmation -> CAS final state。
30. **如何生产化？** 事务租约、per-robot actor、持久化事实、恢复、交通、安全和观测。

## 17. 面试雷区

### 高风险

- Fleet 不是真实多车。
- 取消链不完整。
- heartbeat sweep 不等于 watchdog。
- Collision Monitor 默认关闭。
- 并发领取任务存在 race。
- 巡检 arrival / stabilization / sensor 是 Mock。
- 导航成功后 HTTP writeback 可能失败。
- `RobotExecutionContext` 尚不是完整实机 Adapter。
- 固定点是候选业务点，不是最终现场坐标。
- pytest 不等于实时 Gazebo 或真机验收。

### 中风险

- QoS 没有系统化设计。
- SQLite 没有原子 claim 和完整唯一约束。
- resource wait queue 不持久化。
- battery 未参与调度。
- docking 参数存在不等于充电完成。
- Docker / devcontainer 不等于完整仿真开箱即用。
- demo 脚本的宽泛 `pkill -f` 不适合生产。

### 必须知道但不主动作为亮点

- HTTP dry-run 会模拟回写 `running -> succeeded`。
- API PATCH 没有状态迁移校验。
- assignment 表没有数据库级 active uniqueness。
- `shelf_2` 历史成功过程中触发过 recovery。
- `archive/` 和 `future_extensions/` 不是当前能力。

## 18. 必须背熟的 10 句话

1. 这是单车 Gazebo / Nav2 仿真主线。
2. Mock WMS 只表达最小任务意图。
3. executor 不直接发布 `/cmd_vel`。
4. 导航通过 `NavigateToPose` Action。
5. ready gate 区分未就绪和执行失败。
6. WMS、assignment、execution 状态分离。
7. Fleet 目前只做纯 Python 语义验证。
8. heartbeat sweep 不是硬件 watchdog。
9. 巡检导航真实，传感采集是 Mock。
10. 实机化首先需要统一 Adapter 合同。

## 19. 必须会画的三张图

```text
HTTP / CLI -> Mock WMS -> Executor -> NavigateToPose
             SQLite                    |
                                      Nav2 -> /cmd_vel -> Gazebo
                                             <- /scan /odom
```

```text
pending -> ready gate -> running -> NavigateToPose
        -> succeeded / failed -> SQLite / HTTP projection
```

```text
WMS / Fleet / Inspection
          |
Robot Execution Contract
       /             \
Gazebo / Nav2        Vendor SDK
Adapter              Adapter
```

## 20. 不会时的坦诚回答

### DDS 底层

> 这个项目主要使用 rclpy 和 Nav2 已封装的 DDS 通信，我没有重新实现 DDS discovery 或 RTPS。不过在系统层面，我实际处理了 Topic、Service、Action、TF 和 lifecycle readiness。生产部署时还需要验证 RMW、QoS compatibility 和网络分区行为。

### Nav2 算法

> 我没有自己实现 NavFn 或 MPPI，项目中主要负责插件选择、参数、TF / costmap 输入和运行验证。我能解释它们在导航链中的责任，以及出现贴墙、无进展或 recovery 频繁时应该从哪些输入和参数排查。

### 多车调度

> 当前完成的是 Fleet 状态和调度语义的纯 Python 验证，不是 Gazebo 双车。真实扩展需要先解决 namespace、TF、per-robot Nav2、原子任务租约和交通冲突，所以我不会把它包装成已经完成的多车系统。

### 实机安全

> 当前是仿真项目，没有实现硬件 E-stop 或安全认证。我能说明实机必须补充 command watchdog、唯一控制权、安全雷达、速度限制、断连停止和恢复授权，但这些必须结合具体底盘和现场做硬件验收。

### SDK 经验边界

> 我完成的是 SDK / ROS topic 的只读状态接入和进程隔离验证，还没有完成厂商运动命令闭环。我的接入方法是先验证官方环境和 telemetry，再定义 adapter、错误映射和安全边界，最后在唯一 command owner 下逐级做运动 smoke。

## 21. 代码与证据索引

- 当前设计：`docs/design.md`
- 仿真：`launch/simulation.launch.py`
- 导航：`launch/navigation.launch.py`、`config/nav2_params.yaml`
- SLAM：`launch/slam.launch.py`、`config/slam_toolbox.yaml`
- 固定任务点：`config/task_points.yaml`
- Mock WMS：`amr_warehouse_sim/mock_wms_db_common.py`
- HTTP API：`amr_warehouse_sim/mock_wms_api.py`
- 单车 executor：`amr_warehouse_sim/mock_wms_executor.py`
- task runner：`amr_warehouse_sim/mock_wms_task_runner.py`
- Fleet：`amr_warehouse_sim/fleet/`
- Vendor adapters：`amr_warehouse_sim/integrations/`
- 巡检 P0：`amr_warehouse_sim/inspection/`
- 固定点证据：`docs/wms/reports/fixed_task_points_success_matrix_regression_2026_05_15.md`
- 巡检证据：`docs/inspection/P0_3_NAV2_EXECUTOR_VALIDATION.md`
- 多车 blocker：`docs/fleet/MULTI_ROBOT_DEMO.md`
- Vendor 证据：`docs/fleet/VENDOR_VALIDATION_REPORT.md`
- 自动化测试：`test/`

