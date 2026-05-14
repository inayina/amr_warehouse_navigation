# Mock WMS Executor HTTP Design

日期：`2026-05-14`

## 1. 目的

本文件用于定义 **V3.2 Mock WMS executor over HTTP** 的设计边界，并记录它从设计稿推进到当前主线实现后的收口状态。

当前这个主题已经回答了两个问题：

- executor 如何逐步从直接读取 SQLite 演进为**通过 FastAPI HTTP API 获取任务**
- 在 HTTP 读取和状态回写稳定后，如何把 `--execute` 路径重新接回 Nav2

当前设计与实现共同覆盖：

- 接口边界
- 最小数据流
- 失败处理
- 后续演进顺序

当前仍不做：

- 不做多机器人调度
- 不引入更完整的调度服务

## 2. 当前状态

截至 `2026-05-14`，当前主线已经完成 **V3.2 最小 Mock WMS executor over HTTP**，并保留了清晰的阶段边界。

当前已完成的 HTTP API 支持：

- `GET /health`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `PATCH /tasks/{task_id}/status`

当前这层 API 的职责包括：

- 创建任务
- 查询任务
- 回写最小任务状态

当前它**还不负责**：

- 更完整的 claim / 调度 / 并发协调
- 提供完整 WMS 调度能力

## 3. V3.2 设计目标

V3.2 的核心目标是把 executor 的“任务来源”从：

```text
直接读取 SQLite
```

逐步演进为：

```text
通过 FastAPI HTTP API 获取 pending task
```

也就是说，executor 在 V3.2 之后的理想边界应当是：

- executor 不再直接打开 SQLite 数据库文件
- executor 把“读取任务”的职责交给 HTTP API
- SQLite 仍然可以继续作为 API 背后的数据存储

这样做的主要原因是：

1. 让 executor 与底层存储解耦
2. 让未来状态回写、权限控制、日志扩展和远程调用更自然
3. 为后续接更正式的服务态、调度态预留清晰边界

## 4. 本轮明确边界

本轮设计必须明确保持以下边界：

- 不修改 `launch/navigation.launch.py`
- 不修改 `config/nav2_params.yaml`
- 不修改地图、world、robot model
- 不接 Nav2
- 不发送 `/navigate_to_pose`
- 不引入多机器人调度
- 不引入 MQTT / WebSocket / Web 后台

当前只设计：

- executor 如何通过 HTTP 拉取任务
- executor 本地如何做最小模拟处理
- executor 与 API 之间需要补哪些接口

## 5. 当前 V3.1 与目标 V3.2 的差异

### 5.1 当前 V3.1

当前最小链路是：

```text
SQLite pending task
-> executor 直接读库
-> ready gate / dry-run / execute
-> SQLite status write-back
```

特点：

- executor 与 SQLite 强耦合
- executor 同时承担“取任务”和“执行任务”职责
- 当前已经能验证最小数据层与最小执行链路

### 5.2 目标 V3.2

目标链路应调整为：

```text
SQLite
-> FastAPI HTTP API
-> executor 轮询 HTTP pending task
-> 本地打印 / 模拟处理
-> 后续再接 Nav2
```

特点：

- executor 不再直接读 SQLite
- API 成为任务入口与任务查询边界
- executor 先验证“能否通过 HTTP 拉到任务并处理”，再谈 Nav2 execute

## 6. 最小数据流

本轮推荐的最小 V3.2 数据流如下：

```text
POST /tasks
-> API 写入 SQLite pending task
-> executor 轮询 API 获取 pending task
-> executor 本地打印 / 模拟处理
-> 后续阶段再接 Nav2 execute
```

如果只展开“消费任务”这部分，最小流可以写成：

```text
API /tasks
-> executor 轮询 pending task
-> 本地打印 / 模拟处理
-> 后续再接 Nav2
```

这里的关键点是：

- `POST /tasks` 继续作为当前创建任务入口
- executor 不直接碰 SQLite
- executor 先只做“发现 pending task + 本地模拟处理”
- 真正的 Nav2 execute 保持到后续阶段

## 7. 推荐接口边界

### 7.1 V3.1 已有接口

当前已存在：

- `GET /health`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`

这些接口已经足够支撑：

- 人工创建任务
- 人工查看任务
- 手动确认单条任务内容

但它们还不足以支撑一个更干净的 executor-over-HTTP 消费边界。

### 7.2 V3.2 最小可用读取边界

如果只做最小演进，executor 可以先复用：

```text
GET /tasks
```

做法是：

- executor 轮询 `GET /tasks`
- 在返回结果里筛选 `status=pending`
- 取最早一条 pending task
- 本地打印或模拟处理

这个方案的优点是：

- 当前无需新增接口就能做概念验证
- 可以先验证“HTTP 拉任务”是否通顺

这个方案的缺点是：

- executor 需要在客户端侧自己筛选 `pending`
- 数据量一大就不够自然
- 并发或后续多 executor 时不够稳

### 7.3 更合理的后续接口

为了让 executor 未来边界更清晰，后续建议补以下接口。

建议接口一：

```text
GET /tasks?status=pending&limit=1
```

作用：

- 让 API 负责筛选 pending task
- 让 executor 拿到最小必要数据

建议接口二：

```text
PATCH /tasks/{task_id}/status
```

作用：

- 让 executor 通过 HTTP 回写 `running / succeeded / failed`
- 不再直接写 SQLite

建议接口三：

```text
POST /tasks/claim
```

或等价的 claim 机制。

作用：

- 为后续避免重复消费预留接口形态
- 但当前单 executor、单机最小设计阶段可以先不做

注意：

- 以上都只是 **V3.2 之后的设计建议**
- 本轮不实现这些接口

## 8. executor 在 V3.2 的最小行为

本轮设计建议 executor 在 HTTP 模式下只做下面几步：

1. 定时轮询 API
2. 获取当前 pending task
3. 如果没有 pending task，则打印 no-op 结果
4. 如果有 pending task，则打印任务摘要
5. 本地做一次“模拟处理完成”的输出
6. 暂不接 Nav2，暂不发 goal

也就是说，V3.2 第一阶段的 executor 行为更像：

```text
HTTP consumer / poller
```

而不是：

```text
full Nav2 task executor
```

这样做的好处是：

- 可以先验证 API 与 executor 的边界
- 不把 HTTP 接入和导航执行耦合到同一轮
- 出问题时更容易判断是 API 问题还是 Nav2 问题

## 9. 失败处理设计

本轮只设计最小失败处理，不引入复杂重试或分布式语义。

### 9.1 API 不可达

现象：

- executor 连不上 HTTP 服务

建议处理：

- 本地打印 `api-unreachable`
- 不做 SQLite 兜底直连
- 不切回直接读库

原因：

- V3.2 的目标就是建立清晰的 HTTP 边界
- 一旦保留“失败就偷偷直连 SQLite”，边界会再次混乱

### 9.2 API 返回空队列

现象：

- 当前没有 `pending` task

建议处理：

- 打印 `no-pending-task`
- 本轮视为正常无任务状态，不算失败

### 9.3 API 返回异常数据

现象：

- 缺字段
- `task_id` 非法
- `target_name` 为空
- `status` 不是预期值

建议处理：

- 本地打印 `invalid-task-payload`
- 不尝试执行后续处理
- 后续由 API 层或数据层补更严格校验

### 9.4 模拟处理失败

现象：

- executor 成功拉到任务，但本地处理流程异常

建议处理：

- 当前阶段先只打印失败结果
- 状态回写留给后续 `PATCH /tasks/{task_id}/status` 设计来承接

## 10. 为什么本轮不接 Nav2

本轮故意不把 HTTP executor 直接接到 Nav2，原因是：

1. 当前要验证的是“取任务边界”，不是“导航执行边界”
2. 如果本轮同时接 HTTP 和 Nav2，问题归因会混在一起
3. 当前主线仍要保持 `navigation.launch.py` 和 `config/nav2_params.yaml` 稳定
4. 先做本地打印 / 模拟处理，更符合最小可验证增量

因此，V3.2 的正确节奏应该是：

```text
先验证 HTTP 拉任务
-> 再验证 HTTP 状态回写
-> 最后再把 execute 接回 Nav2
```

## 11. 建议分阶段推进

### 11.1 V3.2-A

目标：

- executor 通过 HTTP 读取任务
- 本地打印 / 模拟处理

不做：

- 不回写状态
- 不接 Nav2

### 11.2 V3.2-B

目标：

- executor 通过 HTTP 回写状态

建议接口：

- `PATCH /tasks/{task_id}/status`

不做：

- 不接多机器人

### 11.3 V3.2-C

目标：

- 在 HTTP 边界稳定后，再把 execute 接回 Nav2

前提：

- 当前 HTTP 读取和状态回写都已稳定
- 任务状态机语义已收口

## 12. 当前结论

截至 `2026-05-14`，V3.2 最合理的设计结论是：

- 当前 HTTP API 已完成 `health / create / list / get / patch-status` 最小闭环
- `mock_wms_executor --api-base-url ...` 已把“取任务”路径从直接读取 SQLite 演进为通过 HTTP 获取 pending task
- HTTP dry-run 会在本地模拟处理阶段回写 `running -> succeeded`
- HTTP `--execute` 会在 ready gate 满足后接回 Nav2，并继续通过 HTTP 回写 `running -> succeeded / failed`
- 当前 V3.2 已形成“HTTP 读任务 + HTTP 回写状态 + 可选 Nav2 execute”的最小闭环
- 当前仍不做多机器人调度，也不把它表述为完整 WMS 调度系统
