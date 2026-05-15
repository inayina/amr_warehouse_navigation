# Mock WMS 可视化录屏演示指南

日期：`2026-05-14`

## 1. 目的

这份文档用于帮助你**可视化跑一遍当前主线 Mock WMS + Nav2 演示链路**，方便录屏展示。

这份指南重点解决三个问题：

- 用哪条路径最适合录屏
- 终端和 GUI 应该怎么摆
- 每一步具体敲什么命令、看什么现象

## 2. 推荐演示路线

如果你的目标是“**最稳、最直观、最适合一次录下来**”，推荐优先使用下面这条主路径：

```text
Gazebo + RViz
→ publish_initial_pose
→ init_mock_wms_db
→ create_mock_task(station_a / station_b)
→ mock_wms_task_runner --execute --max-tasks 2
→ 机器人顺序导航
→ list_mock_tasks 查看 succeeded
```

原因：

- `station_a -> station_b` 已有真实 `SUCCEEDED` 记录
- `mock_wms_task_runner` 比单条 executor 更适合展示“任务队列 -> 导航执行”
- Gazebo 和 RViz 都打开时，画面最适合录屏

如果你还想顺手展示 HTTP API，本指南后面也给了一个**可选加演版**。

## 2.1 一键脚本入口

如果你现在的主要问题是：

- 手工切终端太慢
- `publish_initial_pose`、lifecycle、task runner 的时序容易错过
- 经常遇到 `map_server inactive` 或 `planner_server inactive`

那可以直接优先使用仓库里的自动化脚本：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
./scripts/run_mock_wms_visual_demo.sh --clean
```

这个脚本会自动完成：

```text
启动 navigation.launch.py
→ publish_initial_pose --preset start_zone
→ 等待 Nav2 ready
→ 重置 /tmp/mock_wms_visual_demo.db
→ 创建 station_a、station_b 两条任务
→ 执行 mock_wms_task_runner --execute
→ 打印最终任务状态
```

常用变体：

- GUI 录屏主路径：
  `./scripts/run_mock_wms_visual_demo.sh --clean`
- 已经手动开好了 Gazebo / RViz，只想复用当前会话：
  `./scripts/run_mock_wms_visual_demo.sh --skip-launch`
- 只跑单条任务：
  `./scripts/run_mock_wms_visual_demo.sh --clean station_a`
- 不需要 GUI，只做终端验证：
  `./scripts/run_mock_wms_visual_demo.sh --headless --clean`

如果你想完全理解每一步在做什么，继续看下面的手工分步版。

## 3. 适用范围

本指南只覆盖当前主线已经稳定暴露出来的最小链路：

- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- `config/task_points.yaml`
- `publish_initial_pose --preset start_zone`
- `init_mock_wms_db`
- `create_mock_task`
- `list_mock_tasks`
- `mock_wms_task_runner`
- 可选的 `mock_wms_api` + `mock_wms_executor --api-base-url ...`

本指南不覆盖：

- 修改 Nav2 参数
- 修改地图、world、robot model
- MQTT / WebSocket / Web 后台
- 多机器人

## 4. 录屏前准备

### 4.1 建议画面布局

推荐至少开 3 个终端，加上 Gazebo 和 RViz：

- 终端 A：主 launch
- 终端 B：initial pose 和必要的状态检查
- 终端 C：Mock WMS 任务创建、执行、结果查看
- 终端 D：可选，HTTP API 演示
- Gazebo：显示机器人实际运动
- RViz：显示地图、激光、机器人模型、costmap

推荐录屏摆法：

- 左侧放 Gazebo
- 右侧放 RViz
- 下方横向摆 2~3 个终端

这样观众能同时看到：

- 机器人是否真的在动
- Nav2 是否已经建立地图和定位
- 任务命令是否真的创建 / 执行 / 回写成功

### 4.2 录屏前环境准备

先确认已经编译过当前包：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select amr_warehouse_sim
source install/setup.bash
```

如果你打算把 HTTP API 也录进去，再确认 `.venv` 已就绪：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
source .venv/bin/activate
python -m amr_warehouse_sim.mock_wms_api --help
```

### 4.3 本轮演示建议使用的临时数据库

为了不污染默认数据库，推荐本次录屏统一使用：

```text
/tmp/mock_wms_visual_demo.db
```

每次重录前都先清掉：

```bash
rm -f /tmp/mock_wms_visual_demo.db
```

## 5. 主路径：Gazebo + RViz + SQLite 任务队列顺序执行

这是本指南最推荐的录屏路线。

### 5.1 启动导航主线

在终端 A 执行：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch amr_warehouse_sim navigation.launch.py
```

说明：

- 这里故意不用 `use_gz_gui:=false` 或 `use_rviz:=false`
- 录屏场景下，默认 GUI 版最直观
- 也不建议录屏时使用 `scripts/run_navigation.sh`，因为它会切到 `tmux`，不如直接多窗口更好展示

### 5.2 等画面稳定

建议等待 Gazebo 和 RViz 都加载出来，再继续下一步。

此时你最好能在画面里看到：

- Gazebo 里已经出现 `my_robot`
- RViz 里已经能看到地图
- RViz 里 RobotModel、LaserScan、Map 已正常显示

如果你想在录屏里顺手展示“现在已经 ready”，可以在终端 B 补两条轻量检查：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 topic echo /map --once
ros2 topic echo /scan_filtered --once
```

### 5.3 注入 initial pose

在终端 B 执行：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30
```

预期现象：

- 终端会显示已经找到 `/initialpose` 订阅者并完成发布
- RViz 里的机器人位置会和地图对齐
- 后续 `map -> odom -> base_link` 更容易稳定建立

录屏建议：

- 这一段建议保留在镜头里，因为它能清楚说明“当前定位不是手拖出来的，而是通过主线工具注入的”

### 5.4 可选的 ready 检查

如果你想把“系统已经 ready”也录进去，在终端 B 再执行：

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
```

理想现象：

- 这些节点应尽量显示为 `active`

补充说明：

- fresh session 下，lifecycle 可能有短暂波动
- 如果某个节点一时没有到位，先不要急着重录，等几秒再查一次通常更稳

### 5.5 初始化数据库

在终端 C 执行：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
rm -f /tmp/mock_wms_visual_demo.db
ros2 run amr_warehouse_sim init_mock_wms_db --db /tmp/mock_wms_visual_demo.db
```

预期现象：

- 终端打印 tasks 表初始化完成

### 5.6 创建两条演示任务

继续在终端 C 执行：

```bash
ros2 run amr_warehouse_sim create_mock_task \
  --db /tmp/mock_wms_visual_demo.db \
  --target station_a \
  --task-name demo-station-a

ros2 run amr_warehouse_sim create_mock_task \
  --db /tmp/mock_wms_visual_demo.db \
  --target station_b \
  --task-name demo-station-b
```

然后马上查看一次：

```bash
ros2 run amr_warehouse_sim list_mock_tasks --db /tmp/mock_wms_visual_demo.db
```

预期现象：

- 能看到 2 条 `pending` task
- `target_name` 分别是 `station_a` 和 `station_b`

录屏建议：

- 这一段建议停 1~2 秒，让观众看到“任务已经排进队列，但还没有执行”

### 5.7 顺序执行任务队列

继续在终端 C 执行：

```bash
ros2 run amr_warehouse_sim mock_wms_task_runner \
  --db /tmp/mock_wms_visual_demo.db \
  --execute \
  --max-tasks 2 \
  --ready-timeout 60
```

预期现象：

- 终端会先处理 `station_a`
- 当 ready gate 满足后，发送 `NavigateToPose`
- Gazebo 中机器人开始移动
- RViz 中局部 / 全局 costmap、机器人姿态和路径会跟着变化
- 第一条任务成功后，runner 会继续处理 `station_b`
- 第二条任务成功后，终端会显示队列执行摘要

这段是整场录屏最关键的镜头，建议重点保留：

- 终端 C 的 runner 输出
- Gazebo 中机器人真实移动
- RViz 中地图、激光、机器人模型和 costmap 一起变化

### 5.8 查看最终状态回写

任务执行结束后，在终端 C 再执行一次：

```bash
ros2 run amr_warehouse_sim list_mock_tasks --db /tmp/mock_wms_visual_demo.db
```

预期现象：

- `station_a`、`station_b` 的 `status` 都变成 `succeeded`
- `status_reason` 会记录 Nav2 result，例如 `NavigateToPose result: SUCCEEDED`

这一幕很适合作为收尾镜头，因为它能把：

- 任务创建
- 任务执行
- 状态回写

三个阶段完整闭环展示出来。

## 6. 精简版录屏路径

如果你想把视频时长压短，可以只录一条任务。

把第 5.6 和 5.7 改成下面这样：

```bash
ros2 run amr_warehouse_sim create_mock_task \
  --db /tmp/mock_wms_visual_demo.db \
  --target station_a \
  --task-name demo-station-a
```

```bash
ros2 run amr_warehouse_sim mock_wms_task_runner \
  --db /tmp/mock_wms_visual_demo.db \
  --execute \
  --max-tasks 1 \
  --ready-timeout 60
```

适用场景：

- 想录一个更短的视频
- 只想证明“任务可以变成真实导航动作”
- 不需要强调队列能力

## 7. 可选加演版：把 HTTP API 也录进去

如果你还想展示“任务不只是本地 SQLite CLI 创建，也可以从 HTTP 入口进入”，可以在主路径前面加一个 HTTP 片段。

### 7.1 启动 HTTP API

在终端 D 执行：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
source .venv/bin/activate
python3 -m amr_warehouse_sim.mock_wms_api \
  --db /tmp/mock_wms_visual_demo.db \
  --task-points $PWD/config/task_points.yaml \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level warning
```

说明：

- 这里直接用 `python3 -m amr_warehouse_sim.mock_wms_api`，比录屏时额外设置一堆环境变量更直观
- 这条命令仍然会启动 FastAPI / uvicorn 服务

### 7.2 通过 HTTP 创建任务

新开一个终端，执行：

```bash
curl --noproxy '*' -sS -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"target_name":"station_a","task_name":"http-demo-station-a"}'
```

然后查一下：

```bash
curl --noproxy '*' -sS http://127.0.0.1:8000/tasks
```

预期现象：

- 你能先在终端里证明任务是通过 HTTP 创建出来的
- 然后再切回 Gazebo / RViz / 执行器画面

### 7.3 用 HTTP executor 单条消费任务

如果你要把“HTTP intake + Nav2 execute”也录进去，可以在已经完成第 5.1 到 5.4 的前提下执行：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run amr_warehouse_sim mock_wms_executor \
  --api-base-url http://127.0.0.1:8000 \
  --execute \
  --ready-timeout 60
```

执行后再查一次：

```bash
curl --noproxy '*' -sS http://127.0.0.1:8000/tasks
```

说明：

- 这一条更适合展示“HTTP 创建的任务可以被执行器拉走”
- 但它一次只处理最早一条 `pending` task
- 如果你的重点是“任务队列顺序执行”，还是优先录第 5 节的 `mock_wms_task_runner`

## 8. 录屏口径建议

如果你想让录屏解说更顺，可以按下面这个节奏讲：

1. 先说明当前主线是 Gazebo + Nav2 + fixed task points + 最小 Mock WMS。
2. 展示 Gazebo 和 RViz 已经起来，地图、激光和机器人模型都正常。
3. 用 `publish_initial_pose --preset start_zone` 说明定位入口已经标准化。
4. 展示 `station_a`、`station_b` 两条任务被写入 `pending` 队列。
5. 运行 `mock_wms_task_runner --execute --max-tasks 2`，展示任务如何变成真实导航。
6. 最后展示 SQLite 中两条任务状态都回写成 `succeeded`。

## 9. 最常见卡点与最快恢复方式

### 9.1 Gazebo / RViz 已开，但 runner 提示 ready gate 不满足

优先按这个顺序处理：

1. 等 5~10 秒再重试一次
2. 再执行一次：
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
3. 再查一次 lifecycle：
   `ros2 lifecycle get /map_server`
   `ros2 lifecycle get /bt_navigator`

不要第一反应就去改 `config/nav2_params.yaml`。

### 9.2 `create_mock_task` 返回非法目标点

当前推荐用于录屏的目标点是：

- `station_a`
- `station_b`
- `shelf_1`
- `shelf_2`
- `candidate_dock_a`

不要用：

- `start_zone`

因为它只用于 initial pose，不是当前 Mock WMS 任务目标。

### 9.3 HTTP API 启动时报缺少 `fastapi` 或 `uvicorn`

执行：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
source .venv/bin/activate
pip install -r requirements.txt
```

### 9.4 想重新录一遍

最简单的重置方式：

1. 关闭当前 launch
2. 删除临时库：
   `rm -f /tmp/mock_wms_visual_demo.db`
3. 重启 `navigation.launch.py`
4. 重新注入 initial pose
5. 重新建任务并执行

## 10. 录屏后建议保留的截图

建议至少保留下面 4 张图，后续做 README、汇报或简历材料都很有用：

- Gazebo 中机器人正在移动的画面
- RViz 中地图 + LaserScan + costmap 同屏画面
- `mock_wms_task_runner --execute --max-tasks 2` 的成功终端输出
- `list_mock_tasks` 显示两条任务都为 `succeeded` 的终端输出
