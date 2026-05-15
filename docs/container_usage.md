# Container Usage

本文件说明当前主线下 `Dockerfile` 与 `.devcontainer` 的定位、支持范围和边界。

最后同步：`2026-05-15`

## 1. 当前目标

当前容器入口的目标只有一个：

- 为 `amr_warehouse_sim` 提供一个轻量、可复用的开发环境，覆盖 `ROS 2 Jazzy + Python 依赖 + colcon build + pytest + Mock WMS API`

它的角色是“工程化开发入口”，不是新的仿真运行主线。

## 2. 当前支持什么

当前根目录 `Dockerfile` 和 `.devcontainer/devcontainer.json` 主要支持以下能力：

- `colcon build --symlink-install --packages-select amr_warehouse_sim`
- `pytest test -q`
- `make test`
- `make run-executor`
- `python -m amr_warehouse_sim.mock_wms_api --help`
- `uvicorn scripts.mock_wms_api:create_app --factory --host 0.0.0.0 --port 8000`
- `test/integration/test_mock_wms_http_api.py` 这类不依赖 Gazebo / RViz 的 Mock WMS HTTP API 集成测试

容器镜像中已经预装：

- ROS 2 Jazzy `ros-base`
- `colcon`
- `pytest`
- `fastapi`
- `uvicorn`
- `httpx`
- 当前测试和轻量 CLI 需要的 ROS Python 包

`.devcontainer/post-create.sh` 会在容器创建后自动执行一次：

```bash
cd /workspaces/ros2_ws
colcon build --symlink-install --packages-select amr_warehouse_sim
```

这样 devcontainer 打开后就能直接进入当前工作区继续测试或调试。

## 3. 当前不支持什么

当前容器入口明确不以这些能力为目标：

- 不保证容器内完整启动 Gazebo GUI
- 不保证容器内完整启动 RViz
- 不把容器作为当前 Nav2 live readiness / `/navigate_to_pose` 运行时验证主入口
- 不在容器内接管当前 `navigation.launch.py` 的正式验收链路
- 不在本轮引入 X11、GPU、音频、图形转发或桌面仿真兼容层

原因很简单：

- 当前主线的 Gazebo / RViz / Nav2 运行时验证已经在本机链路上形成基线；
- 这次只想补回“轻量工程化入口”，避免容器层反向影响当前导航主线。

## 4. 本机运行与容器运行的边界

建议把边界理解为下面两层：

### 更适合在容器内做的事

- 安装和统一 Python 依赖
- `colcon build`
- `pytest`
- Mock WMS SQLite / CLI / HTTP API 相关开发
- 只依赖 Python / ROS 包导入的 contract test、smoke test

### 仍然以本机为主的事

- `ros2 launch amr_warehouse_sim navigation.launch.py`
- Gazebo 世界与机器人模型运行
- RViz 可视化
- AMCL / Nav2 lifecycle 真正进入 `active`
- `publish_initial_pose`
- `mock_wms_executor --execute`
- 需要 `/navigate_to_pose`、TF、ready gate 真实在线验证的场景回归

当前主线判断仍然是：

- 容器负责“开发、构建、静态/轻量验证”
- 本机负责“Gazebo / Nav2 / 运行时闭环验证”

## 5. 快速使用

### 5.1 直接构建镜像

在仓库根目录执行：

```bash
docker build -t amr-warehouse-sim-dev .
```

### 5.2 用临时容器做轻量验证

```bash
docker run --rm -it \
  -p 8000:8000 \
  -v "$PWD":/workspaces/ros2_ws/src/amr_warehouse_sim \
  amr-warehouse-sim-dev bash
```

进入容器后，常用命令是：

```bash
cd /workspaces/ros2_ws
colcon build --symlink-install --packages-select amr_warehouse_sim

cd /workspaces/ros2_ws/src/amr_warehouse_sim
pytest test -q
make test
make run-executor
python -m amr_warehouse_sim.mock_wms_api --help
uvicorn scripts.mock_wms_api:create_app --factory --host 0.0.0.0 --port 8000
```

### 5.3 用 devcontainer

如果本机使用 VS Code / Dev Containers：

1. 在仓库根目录打开项目
2. 选择 `Reopen in Container`
3. 等待 `.devcontainer/post-create.sh` 完成首次 `colcon build`

容器内源码目录：

```text
/workspaces/ros2_ws/src/amr_warehouse_sim
```

ROS 工作区根目录：

```text
/workspaces/ros2_ws
```

## 6. 推荐容器内验收命令

如果只做这次容器入口的最小回归，建议优先执行：

```bash
cd /workspaces/ros2_ws
colcon build --symlink-install --packages-select amr_warehouse_sim

cd /workspaces/ros2_ws/src/amr_warehouse_sim
pytest test -q
pytest test/integration/test_mock_wms_http_api.py -q
python -m amr_warehouse_sim.mock_wms_api --help
```

如果要确认 HTTP API 能启动，再额外执行：

```bash
cd /workspaces/ros2_ws/src/amr_warehouse_sim
uvicorn scripts.mock_wms_api:create_app --factory --host 0.0.0.0 --port 8000
```

然后在另一个终端请求：

```bash
curl http://127.0.0.1:8000/health
```

## 7. 后续扩展方向

后续如果要继续推进容器化，建议单独开下一轮，把范围限定为：

- Gazebo / Nav2 headless 运行时依赖梳理
- ready gate 运行时验证是否能迁入容器
- 是否需要单独的 runtime 镜像或 compose 文件

在那之前，当前容器入口请继续保持“轻量开发环境”的定位，不要反向改动现有本机主流程。
