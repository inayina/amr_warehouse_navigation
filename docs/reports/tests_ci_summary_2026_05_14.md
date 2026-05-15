# 测试与 CI 摘要（2026-05-14）

目的：提供一份简明说明，帮助在本地运行测试集，并给出推荐的 CI 检查方式。

## 本地快速命令

- 使用 `Makefile` 辅助入口运行单元测试和集成测试：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
make test
```

- 如果本地已经准备好 Python 环境，也可以直接执行：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
python3 -m pytest test -q
```

- `colcon` 风格运行方式（在完整工作空间内执行）：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon test --packages-select amr_warehouse_sim
colcon test-result --verbose
```

## 说明与预期

- 当前测试覆盖：SQLite Mock WMS 数据库、HTTP API 契约、executor / runner 契约，以及 Nav2 ready-gate 逻辑（单元测试里使用 mock 方式验证）。
- 建议使用 Python 3.12，并安装 `fastapi`、`uvicorn`、`httpx` 和 `pytest`（见 `requirements.txt`）。
- `make test` 会优先使用 `.venv`；如果 `.venv` 不存在，则回退到当前 shell 的 `python3`。

## CI 建议

- 在 Python 3.12 环境中运行 `make test`。
- 不依赖 ROS 的轻量 CI 仍然可以运行纯 Python 测试；依赖 ROS 的功能 smoke test 应在缺少 ROS 2 Jazzy 包时跳过。
- 如果要做完整集成 CI，建议在 runner 镜像中安装系统级 ROS 依赖，或直接使用已安装 Jazzy 的预构建容器镜像。
- 建议在 CI 运行之间缓存 pip 安装结果和虚拟环境，并把 `make test` 作为最终校验步骤。
- 如果集成任务会预置 ROS 2 和 Gazebo，也可以在 CI 中额外执行 `colcon test`。

## 常见排障

- 缺少 Python 包：在虚拟环境中执行 `pip install -r requirements.txt`。
- ROS 相关测试要求先 source ROS 2 Jazzy 环境；在轻量 CI 中应跳过或显式 gate 较重的集成测试。
