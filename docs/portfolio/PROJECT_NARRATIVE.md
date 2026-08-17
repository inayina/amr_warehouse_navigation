# PROJECT_NARRATIVE — AMR Warehouse Navigation（求职叙事）

> 本文档是 `amr_warehouse_navigation` 的求职叙事索引：定位 → 技术栈 → 四阶段落地 → 验证与证据现状 → 能证明/不能证明 → 跨仓集成 → 已知问题 → 面试可讲点 → 边界声明。
> 证据纪律约定（与 WS3 审计报告一致）：【已实现】= 直接代码/文件证据；【文档声明】= README / docs / AGENTS.md 原文；【推断】= 基于证据的合理推断；【未确认】= 未实际运行验证。
> 事实依据：只读审计报告 `ws3_amr-dashboard.md`（2026-08-05）+ 仓库内代码与文档；本文档不新增任何未经审计的数字。

---

## 1. 仓库定位

- GitHub 仓库名：`inayina/amr_warehouse_navigation`；ROS 2 包名仍为 `amr_warehouse_sim`（本地路径 `~/ros2_ws/src/amr_warehouse_sim`）。
- 一句话定位：基于 **ROS 2 Jazzy + Gazebo Harmonic** 的 AMR 仓储仿真仓库，覆盖「SLAM 建图 → Nav2 导航 → 固定任务点执行 → 最小 Mock WMS 任务闭环」，并作为 robot-ops-dashboard 的 AMR 数据来源。【已实现】AGENTS.md / design.md / README 三处定位口径一致。
- 明确边界：**不是完整 WMS、不是多机器人调度系统、不是生产级后端，也不直接代表真实底盘控制**。【文档声明】README 原文，与代码结构相符。

## 2. 技术栈

| 层 | 技术 | 证据 |
|---|---|---|
| 仿真 | Gazebo Harmonic（`gz sim -r`）+ ros_gz_bridge | `launch/slam.launch.py`、`worlds/`、`models/`【已实现】 |
| 建图 | slam_toolbox + laser_filters（`/scan → /scan_filtered`） | `config/slam_toolbox.yaml`、`config/laser_filters.yaml`【已实现】 |
| 导航 | Nav2（map_server / AMCL / planner / controller / bt_navigator / NavigateToPose） | `launch/navigation.launch.py`、`config/nav2_params.yaml`、`rviz/nav2.rviz`【已实现】 |
| 任务层 | Python / SQLite / FastAPI + uvicorn（最小 Mock WMS） | `amr_warehouse_sim/mock_wms_*.py`、`scripts/`【已实现】 |
| 测试 | pytest + colcon test（四层） | `test/`（data/functional/integration/scenarios）、`.github/workflows/python-test.yml`【已实现】 |

## 3. 核心能力与阶段落地（四阶段）

### V1 — SLAM 建图闭环 【已实现】（链路文件齐全；运行时行为未复核）

- 链路：`Gazebo → /scan → laser_filters /scan_filtered → odom+TF → slam_toolbox → /map → maps/warehouse.yaml`。【文档声明】AGENTS.md 原文，链路文件全部存在【已实现】。
- 证据文件：`launch/slam.launch.py`、`config/slam_toolbox.yaml`、`config/laser_filters.yaml`、`amr_warehouse_sim/odom_tf_node.py`、`maps/warehouse_slam.pgm`（103 KB）。
- 验证文档：建图结果以 `maps/warehouse.yaml` + `docs/reports/` 记录为证据；**本次审计未启动 Gazebo 实跑建图** → 运行时行为【未确认】。

### V2 — Nav2 导航基线 【已实现】（链路文件齐全；运行时行为未复核）

- 链路：`maps/warehouse.yaml → nav2_map_server → AMCL → Nav2 planner/controller → /cmd_vel → Gazebo robot`。【文档声明】AGENTS.md 原文。
- 证据文件：`launch/navigation.launch.py`（`slam: False`、默认 map 与 params）、`config/nav2_params.yaml`、`scripts/run_navigation.sh`、`rviz/nav2.rviz`。【已实现】
- 关键一致性：`maps/warehouse.yaml` 内容与 `docs/design.md` 4.2 所列 YAML **逐字节一致**（`image: warehouse_slam.pgm / trinary / 0.050 / origin [-8.008,-8.174,0]`）。【已实现】审计比对确认。
- 验证文档：`docs/reports/`（含 `test_report_2026_05_12.md` 等）。

### V2.2 — 固定任务点 【已实现】落地；点位验证状态见 §7

- `config/task_points.yaml` 为固定任务点**唯一主线输入**：`start_zone` + `station_a` / `station_b` / `shelf_1` / `shelf_2` / `candidate_dock_a` 共 6 点（map frame）。【已实现】
- 定位入口：`publish_initial_pose --preset start_zone`（`scripts/publish_initial_pose.py`、`amr_warehouse_sim/initial_pose_publisher.py`）。【已实现】
- 验证文档：`docs/reports/repeat_navigation_test_report_2026_05_13.md`、`docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md`。【已实现】文件存在。

### V3 — 最小 Mock WMS 【已实现】全部落地

- SQLite 数据层：`init_mock_wms_db.py`、`create_mock_task.py`、`list_mock_tasks.py`、`mock_wms_db_common.py`（包 + scripts 双份入口）、`data/mock_wms.db`。【已实现】
- executor：`mock_wms_executor.py`（ready gate + `NavigateToPose` + `--dry-run / --execute`）。【已实现】grep 证实。
- runner：`mock_wms_task_runner.py`。【已实现】
- HTTP API：`scripts/mock_wms_api.py`（薄封装）→ `amr_warehouse_sim/mock_wms_api.py`，共 **5 端点**：`GET /health`、`POST /tasks`、`GET /tasks`、`GET /tasks/{task_id}`、`PATCH /tasks/{task_id}/status`，与 README 列表完全一致。【已实现】
- 边界声明与代码一致：HTTP 层只做 CRUD + status writeback，**不接 Nav2 execute**（executor 才是任务到 Nav2 action 的执行边界）。【已实现】
- 历史入口隔离：`mock_wms_runner` 不作为主线默认入口（AGENTS.md 禁止项），`archive/`、`future_extensions/` 保留历史逻辑。【已实现】符合约束。

## 4. 验证与证据现状

- **9 份 WMS 验证报告**（`docs/wms/reports/`，2026-05-13 ~ 05-15）：`mock_wms_executor_execute_validation_2026_05_13`、`mock_wms_task_runner_live_validation_2026_05_13`、`wms_task_points_readiness_report_2026_05_13`、`mock_wms_http_api_validation_2026_05_14`、`mock_wms_http_executor_end_to_end_validation_2026_05_14`、`fixed_task_points_success_matrix_regression_2026_05_15`、`headless_nav2_ready_integration_validation_2026_05_15`、`mock_wms_not_ready_guard_runtime_validation_2026_05_15`、`mock_wms_queue_restart_regression_2026_05_15`。【已实现】文件存在。
- `maps/warehouse.yaml` 与 design.md 4.2 **逐字节一致**。【已实现】
- 四层测试结构：`test/data`（3）、`test/functional`（2）、`test/integration`（7）、`test/scenarios`（4 个场景 spec 文件 + README）；CI workflow `python-test.yml` 存在。【已实现】
- **「63 passed（2026-05-14）」为文档声明**：README / design / roadmap 三处口径一致，但本次审计**未实际运行测试复核**（只读约束）→【文档声明】【未确认】。

## 5. 能证明 / 不能证明清单

**能证明（代码/文件级证据）**
- 四阶段链路文件齐全，阶段口径在 AGENTS.md / design.md / roadmap.md 三份文档一致。【已实现】
- Mock WMS 5 端点、executor 的 ready gate / dry-run / execute、SQLite 数据层全部落地。【已实现】
- `warehouse.yaml` 逐字节一致；`task_points.yaml` 6 点存在；HTTP 层不接 Nav2 execute 的边界声明与代码一致。【已实现】
- commit 历史阶段清晰可追溯：2026-03-09 初始化 → V1（04-24）→ V2（04-25）→ 任务点 + WMS 数据层（05-13）→ V3 + 测试 + CI（05-14）→ 文档收口（05-27），工作区 clean。【已实现】`git log` 证据。

**不能证明（未验证）**
- 「63 passed」未复核。【未确认】
- V1/V2/V3 的运行时行为（建图、导航、execute 成功）未启动 Gazebo/ROS 实跑。【未确认】
- GitHub 远端状态未核对（本地 HEAD 在 `main`）。【未确认】

## 6. 跨仓集成关系（dashboard 消费本仓）

dashboard 通过 HTTP adapter 消费本仓 Mock WMS API，审计逐端点核对：

| dashboard 调用 | 本仓端点 | 判定 |
|---|---|---|
| `GET /health`（健康检查） | `@app.get('/health')` | ✅ 一致 |
| `GET /tasks`（任务列表） | `@app.get('/tasks')` → `{count, tasks}` | ✅ 一致（dashboard 兼容 list / `{"data":[]}` / `{"tasks":[]}` 三种形状） |
| `POST /tasks`（创建，`{target_name, task_name}`） | `@app.post('/tasks')`（target_name 必填、task_name 可选，返回 201） | ✅ 一致（payload 字段完全吻合） |
| —（dashboard 不调用） | `GET /tasks/{task_id}`、`PATCH /tasks/{task_id}/status` | ✅ 无冲突（状态回写由本仓 executor 负责，边界清晰） |

- **状态映射 5 种全覆盖**：本仓任务行 `status` 枚举（`pending / running / succeeded / failed / canceled`）在 dashboard `task_mapper.py` 中全部有映射（`pending→queued`、`succeeded→completed`、`canceled→cancelled` 等）。【已实现】
- 默认端口一致：本仓 API 默认 `--port 8000` ↔ dashboard `AMR_API_BASE_URL=http://127.0.0.1:8000`。【已实现】
- 集成边界：dashboard 不直接调度 Nav2；任务执行与状态回写都在本仓。【已实现】

## 7. 已知问题（如实列出）

1. **`dock_a` 为 candidate 未正式验证（中）**：`task_points.yaml` 中只有 `candidate_dock_a`，注释明确「尚未完成正式 3 轮重复验证」；Mock WMS 靠 `TARGET_NAME_FALLBACKS`（`dock_a→candidate_dock_a`）兜底。roadmap 的 V2.2 `[x]` 完成标记与 task_points 的 candidate 措辞存在口径张力（station_a/b、shelf_1/2 同理：有 2026-05-13 就绪性报告支撑「至少一次成功」，但坐标仍标 candidate）。**面试统一口径**：「点位已完成首轮真实导航验证，正式 3 轮回归证据持续积累中」。
2. **`start_zone` 白名单缺失（中，跨仓 D1）**：`SUPPORTED_V3_TARGET_NAMES` 不含 `start_zone`，而 dashboard 前端允许 `start_zone` 作为 dropoff → 用户手动选择时上游 `POST /tasks` 返回 400 ValueError。
3. `maps/` 存在 `warehouse_slam_gazebo_aligned_candidate.yaml/.pgm` 候选对齐文件，未被 design.md 地图章节提及（低）。
4. fresh-session 启动稳定性仍有波动（`docs/logs` 有诚实记录）——面试被追问导航稳定性时主动承认。

## 8. 面试可讲点

1. **四阶段交付故事线**：「把一个大目标切成可验证的阶段」——建图闭环 → 导航基线 → 固定任务点 → 最小任务闭环，每阶段一个验证文档，commit 历史可追溯。
2. **ready gate / dry-run / execute 验证流程**：先 dry-run 检查前置条件，再单条短距离 execute 观察 `/navigate_to_pose` 与状态回写，最后 HTTP 端到端——「如何证明任务执行不是玄学」。
3. **文档工程化闭环**：「设计 → 实现 → 证据」三件套：design/roadmap 阶段口径 + 9 份 WMS 报告 + 四层测试 + CI。
4. **跨仓 HTTP 契约对齐**：双端端点/方法/payload 一致、状态机映射 5 状态全覆盖、三种响应形状兼容——系统集成能力的直接素材。
5. **历史入口隔离的工程纪律**：`mock_wms_runner` 这类扩展入口明确不进主线，避免主线被历史逻辑污染。

## 9. 边界声明

- 本仓库是**最小 Mock WMS**，不是完整 WMS / 订单 / 库位 / Web 后台 / 常驻调度系统；不引入多车协同。
- Nav2 输出 `/cmd_vel` 驱动 **Gazebo 仿真机器人，不驱动真实电机**；不宣称真实底盘控制能力。
- 「63 passed」为文档声明，未在当前环境复核；V1/V2 运行时行为未在本叙事撰写时重新实跑。
