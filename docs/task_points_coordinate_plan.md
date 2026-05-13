# Task Points Candidate Coordinate Plan

日期：`2026-05-13`

本文件只给出 `station_a`、`station_b`、`shelf_1`、`shelf_2` 的一版 `candidate coordinates` 设计。

边界：

- 不直接改写 `config/task_points.yaml`
- 不宣称这些点已经测试通过
- 不修改 `navigation.launch.py`、`config/nav2_params.yaml`、地图、world、robot model

## 1. 设计依据

本轮候选坐标基于以下现有主线信息整理：

- 当前地图入口：`maps/warehouse.yaml`
  - `image: warehouse_slam.pgm`
  - `resolution: 0.050`
  - `origin: [-8.008, -8.174, 0]`
- 当前任务点主线入口：`config/task_points.yaml`
  - `start_zone` 已固定在 `map: (0.0, 0.0, 0.0)`
  - `station_a`、`station_b`、`shelf_1`、`shelf_2` 仍为 `TBD`
- 当前仓库语义来源：`worlds/warehouse_full.world`
  - `charging_station`：`(-6.4, -5.8)`
  - `packing_station`：`(6.2, -4.8)`
  - `rack_inner_left`：`(-1.55, 2.5)`
  - `rack_inner_right`：`(1.55, 2.5)`
  - `rack_outer_left`：`(-4.0, -1.5)`
  - `rack_outer_right`：`(4.0, -1.5)`
  - `loading_zone_visual`：`(0.0, -6.2)`
- 现有历史 scene-aligned 候选参考：`future_extensions/wms_integration/config/waypoints.json`
  - `dock_a`、`buffer_1`、`staging_1`、`inspection_point`

## 2. 设计思路

当前语义上已经有一组南侧/东侧历史候选点：

- `candidate_dock_a` 对应南侧 loading approach
- `buffer_1` 对应南侧中转通道
- `staging_1` 对应东南 staging lane
- `inspection_point` 对应东侧 inspection aisle

因此这版候选坐标设计刻意做了两件事：

1. `station_a`、`station_b` 优先锚定 world 里已经命名的 service station 语义：
   - `charging_station`
   - `packing_station`
2. `shelf_1`、`shelf_2` 优先锚定上半区两排 inner racks，避免和当前南侧 corridor 历史候选点严重重叠。

这只是第一版设计，不代表这些点已经通过 Nav2 goal 验证。

## 3. Candidate Coordinates

| Point Name | X | Y | Yaw | 设计理由 | 是否适合作为 Nav2 goal |
| --- | --- | --- | --- | --- | --- |
| `station_a` | `-5.30` | `-5.80` | `3.14` | 语义上对应 `charging_station (-6.4, -5.8)` 的东侧 approach 点。候选点放在充电站东侧，机器人面朝西，可作为“到充电位前停靠”的第一版 station 候选。这样也能避免和当前 `candidate_dock_a` 的南侧 loading approach 完全重叠。 | `是（candidate / 中等把握）`。西南角开阔，语义明确；但未做真实 goal 验证，仍需看 localization 和 local costmap 在西南角是否稳定。 |
| `station_b` | `5.00` | `-4.80` | `0.00` | 语义上对应 `packing_station (6.2, -4.8)` 的西侧 approach 点。候选点放在 packing station 西侧，机器人面朝东，适合作为“到打包工位前停靠”的第一版 station 候选。它也与历史 `staging_1 (4.6, -3.8)` 保持邻近，便于后续比较 east-side lane 的可达性。 | `是（candidate / 中等偏高把握）`。东南区域已有 `staging_1` 语义参考，但该点比 `staging_1` 更贴近 packing station，本身仍未真实验证。 |
| `shelf_1` | `-2.75` | `2.50` | `0.00` | 语义上对应 `rack_inner_left (-1.55, 2.5)` 的西侧 shelf-side 点。候选点落在左 inner rack 外侧通道，机器人面朝东，适合作为“靠左内侧货架拣选/巡视”的第一版 shelf 候选。相比把 shelf 点放在南侧 outer rack，这个点能把覆盖范围拉到仓库上半区。 | `是（candidate / 中等把握）`。语义清晰，且与 station 点空间分布更均衡；但上半区通道尚未做真实 goal 验证。 |
| `shelf_2` | `2.75` | `2.50` | `3.14` | 语义上对应 `rack_inner_right (1.55, 2.5)` 的东侧 shelf-side 点。候选点落在右 inner rack 外侧通道，机器人面朝西，与 `shelf_1` 形成左右对称的一对 shelf-side 候选。这样后续重复导航时可以比较左右 rack approach 的稳定性。 | `是（candidate / 中等把握）`。几何上与 `shelf_1` 对称，语义合理；但 east half 的导航仍需真实补测，不可直接写成已通过。 |

## 4. 语义映射说明

建议把这四个点先按下面的语义理解使用：

- `station_a`
  - 候选语义：`charging station approach`
- `station_b`
  - 候选语义：`packing station approach`
- `shelf_1`
  - 候选语义：`left inner rack shelf-side goal`
- `shelf_2`
  - 候选语义：`right inner rack shelf-side goal`

这样做的好处是：

- station 点和 shelf 点不会全都堆在南侧 corridor
- 点位命名和 world 里的可见语义能一一对应
- 后续 WMS / task layer 如果只消费点名，也更容易理解任务含义

## 5. 当前不直接写回主线的原因

当前不直接把这些值写进 `config/task_points.yaml`，原因有三点：

1. 这些坐标还只是设计候选，不是已验证结果。
2. `docs/reports/repeat_navigation_test_report_2026_05_13.md` 已经表明：当前 headless 测试里仍存在 lifecycle / action graph 波动，不能把“设计上看起来合理”直接写成“主线可执行”。
3. 仓库约束要求先最小、可复核地推进；因此先落文档，再决定是否进入真实补测。

## 6. 如果要进入真实测试，下一步该改哪里

如果你准备把这版候选坐标转成真实测试输入，优先修改的配置文件是：

- `config/task_points.yaml`

建议只替换这四个点当前的 `TBD`：

- `station_a`
- `station_b`
- `shelf_1`
- `shelf_2`

可选同步文件：

- `docs/fixed_task_points.md`
  - 把对应行从 `pending backfill` 改成 `candidate backfill`

不建议这一步同时改：

- `navigation.launch.py`
- `config/nav2_params.yaml`
- `maps/warehouse.yaml`
- `worlds/warehouse_full.world`

## 7. 建议补测方式

如果要把候选坐标推进成真实测试，建议按下面顺序补测：

1. 更新 `config/task_points.yaml`
   - 只回填这四个点的 `x / y / yaw`
2. 启动当前主线：
   - `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
3. 注入初始位姿：
   - `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
4. 先检查前提，不满足就 `SKIPPED`
   - `ros2 lifecycle get /map_server`
   - `ros2 lifecycle get /amcl`
   - `ros2 lifecycle get /planner_server`
   - `ros2 lifecycle get /controller_server`
   - `ros2 lifecycle get /bt_navigator`
   - `ros2 run tf2_ros tf2_echo map odom`
   - `ros2 action info /navigate_to_pose`
5. 只在 lifecycle 全 `active [3]`、`map -> odom` 可用、`/navigate_to_pose` 有可用 server 时发 goal
6. 每个点至少记录：
   - point name
   - goal x / y / yaw
   - lifecycle
   - TF
   - action
   - 结果
   - 原因
7. 把真实结果写回新的测试报告
   - 建议继续沿用日期化报告，而不是直接把候选设计文档改写成“已通过”

## 8. 建议采用顺序

如果你想先从风险更低的点开始，建议顺序如下：

1. `station_b`
   - 靠近已有 east-side 历史候选区域
2. `station_a`
   - 语义明确，但西南角尚未专门验证
3. `shelf_1`
   - 开始进入上半区 rack 目标
4. `shelf_2`
   - 对称补齐另一侧 shelf 目标

## 9. 结论

这四个坐标目前都只能叫：

- `candidate coordinates`

不能叫：

- `validated goals`
- `passed task points`
- `mainline confirmed coordinates`

当前最合适的下一步不是改 Nav2 参数，而是：

1. 先评审这版坐标设计是否符合你心中的仓库语义
2. 如需进入真实测试，再把候选值写入 `config/task_points.yaml`
3. 按现有报告格式逐点补测并记录真实结果
