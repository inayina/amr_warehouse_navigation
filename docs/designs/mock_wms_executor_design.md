# Mock WMS Executor Design

日期：`2026-05-13`

## 1. 目的

本文件定义 V3.1 `task_to_nav2_adapter / Mock WMS Task Executor` 的最小闭环边界。

当前目标不是做复杂调度，而是验证下面这条最小链路：

```text
SQLite pending task
-> config/task_points.yaml
-> Nav2 ready gate
-> /navigate_to_pose
-> SQLite status write-back
```

## 2. 范围

当前范围只包括：

- 从 SQLite 中读取最早一条 `status=pending` 的任务
- 根据 `target_name` 从 `config/task_points.yaml` 解析 `frame_id / x / y / yaw`
- 检查最小 Nav2 ready gate
- 默认 dry-run，不发 goal
- 显式传入 `--execute` 后才允许发送 `/navigate_to_pose`
- 把状态和最近一次原因回写到 SQLite

当前明确不做：

- 不修改 `launch/navigation.launch.py`
- 不修改 `config/nav2_params.yaml`
- 不修改地图、world、robot model
- 不直接发布 `/cmd_vel`
- 不引入 HTTP / MQTT / Web 后台
- 不做多机器人
- 不做复杂调度

## 3. 输入与输出

输入：

- SQLite 数据库：默认 `data/mock_wms.db`
- 任务点配置：默认 `config/task_points.yaml`

输出：

- 对应任务的 `status`
- 对应任务的 `status_reason`
- CLI 一次性执行结果

## 4. Ready Gate

当前最小 ready gate 必须同时满足：

- `/map_server` lifecycle 为 `active`
- `/amcl` lifecycle 为 `active`
- `/planner_server` lifecycle 为 `active`
- `/controller_server` lifecycle 为 `active`
- `/bt_navigator` lifecycle 为 `active`
- `map -> odom` TF 可用
- `/navigate_to_pose` action server 可用

说明：

- 这组 gate 直接对应 `docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md` 中发 goal 前的人工前置条件
- 当前 executor 只做一次性检查，不负责 startup stability 诊断

## 5. 状态机

当前最小状态机如下：

```text
no pending task
  -> no-op

pending
  -> failed        (target_name 无法从 task_points.yaml 合法解析)
  -> pending       (ready gate 不满足，记录 status_reason)
  -> pending       (dry-run 且 ready gate 满足，记录 status_reason)
  -> running       (仅 execute 模式且 ready gate 满足)

running
  -> succeeded     (NavigateToPose result = SUCCEEDED)
  -> failed        (ABORTED / CANCELED / timeout / rejected / other non-success)
```

当前设计选择：

- ready gate 不满足时，不把任务写成 `failed`
- 当前也不引入新的 `skipped` SQLite 状态
- 本轮选择“保持 `pending` + 写入 `status_reason`”，这样更适合后续重试

## 6. Dry-Run 与 Execute

### 6.1 Dry-Run

默认行为：

- 读取最早一条 `pending` task
- 解析目标点
- 检查 ready gate
- 不发送 `/navigate_to_pose`
- 任务仍保持 `pending`
- `status_reason` 更新为最近一次 dry-run 结果

### 6.2 Execute

只有显式传入：

```bash
python3 scripts/run_mock_wms_executor.py --execute
```

才允许：

- 通过 ready gate 后把任务写成 `running`
- 调用 `/navigate_to_pose`
- 根据结果回写 `succeeded` 或 `failed`

## 7. 测试约束

自动化测试当前不需要真的启动 Nav2。

测试策略：

- 用 fake ready gate / fake navigator 覆盖状态机逻辑
- 重点覆盖：
  - `no pending task`
  - `unknown target`
  - `ready gate false`
  - `ready gate true + succeeded`
  - `ready gate true + failed`
  - `dry-run` 不把任务改成 `running`

## 8. 当前限制

- 当前 executor 一次只处理一条最早 `pending` task
- 当前没有任务锁、并发抢占和多 executor 协调
- 当前只记录最近一次 `status_reason`，不是完整事件历史
- 当前仍受 V2 Nav2 startup stability 波动影响
- `station_a`、`station_b`、`shelf_1`、`shelf_2` 仍应视为 candidate coordinates，不宣称最终生产点位
