# Mock WMS CLI / 入口桥接说明

日期：`2026-05-14`

## 1. 目的

本文件专门解释一个容易让人困惑的问题：

- 为什么 `amr_warehouse_sim/` 目录下新增了这么多文件
- 为什么其中有些文件只有几行
- 这些短文件和 `scripts/`、`setup.py`、测试文件之间到底是什么关系

本文只解释当前主线里的 Mock WMS CLI / executor / task runner 入口结构，不修改 Nav2 稳定基线，不讨论地图、world 或机器人模型。

## 2. 当前现象

在这轮整理后，仓库里同时出现了下面几类文件：

- `scripts/init_mock_wms_db.py`
- `scripts/create_mock_task.py`
- `scripts/list_mock_tasks.py`
- `scripts/run_mock_wms_executor.py`
- `amr_warehouse_sim/init_mock_wms_db.py`
- `amr_warehouse_sim/create_mock_task.py`
- `amr_warehouse_sim/list_mock_tasks.py`
- `amr_warehouse_sim/mock_wms_executor.py`
- `amr_warehouse_sim/mock_wms_task_runner.py`
- `amr_warehouse_sim/_script_entry.py`

其中最容易引起疑问的是：

- 为什么 `scripts/` 里已经有脚本了，`amr_warehouse_sim/` 里还要再来一份
- 为什么 `amr_warehouse_sim/init_mock_wms_db.py` 这种文件只有几行，看起来像“转一手”

答案是：这些文件并不都在承载业务逻辑，它们分属不同层级。

## 3. 这批文件分成哪几层

### 3.1 包入口包装层

下面这些文件大多都很短：

- `amr_warehouse_sim/init_mock_wms_db.py`
- `amr_warehouse_sim/create_mock_task.py`
- `amr_warehouse_sim/list_mock_tasks.py`
- `amr_warehouse_sim/mock_wms_executor.py`

它们的职责不是重写数据库或导航逻辑，而是提供“包内模块入口”。

原因是 `ros2 run` 和 `setup.py` 的 `console_scripts` 需要指向：

```text
包名.模块名:main
```

也就是说，想让下面这些命令成立：

```bash
ros2 run amr_warehouse_sim init_mock_wms_db
ros2 run amr_warehouse_sim create_mock_task
ros2 run amr_warehouse_sim list_mock_tasks
ros2 run amr_warehouse_sim mock_wms_executor
```

就必须在 `amr_warehouse_sim/` 包目录下真的存在同名模块。

因此，这些“只有几行”的文件不是多余代码，而是 ROS 2 包入口适配层。

### 3.2 公共加载层

`amr_warehouse_sim/_script_entry.py`

这个文件的作用是把“去哪里找真正脚本、怎么动态加载、怎么拿到 `main()`”这套通用逻辑收拢到一个地方。

它负责：

- 先找源码目录下的 `scripts/*.py`
- 如果当前环境是已安装包，再找 `share/amr_warehouse_sim/scripts/*.py`
- 用 `importlib` 动态加载脚本模块
- 取出脚本里的 `main()` 并返回

这样做的好处是：

- 每个包入口文件都不用重复写一遍加载逻辑
- 既兼容源码内直接运行，也兼容安装后的 `ros2 run`

### 3.3 脚本实现层

下面这些文件才是原本的 CLI / 执行器实现主体：

- `scripts/init_mock_wms_db.py`
- `scripts/create_mock_task.py`
- `scripts/list_mock_tasks.py`
- `scripts/run_mock_wms_executor.py`

这里才有真正的参数解析、SQLite 处理、ready gate 检查、状态回写等逻辑。

例如：

- `scripts/init_mock_wms_db.py`
  负责初始化数据库
- `scripts/create_mock_task.py`
  负责从 `config/task_points.yaml` 创建一条 `pending` task
- `scripts/list_mock_tasks.py`
  负责把任务表打印出来
- `scripts/run_mock_wms_executor.py`
  负责读取最早一条 `pending` task，检查 ready gate，并在 execute 模式下发送 `/navigate_to_pose`

### 3.4 新增功能层

`amr_warehouse_sim/mock_wms_task_runner.py`

这个文件和前面的短包装层不同，它不是单纯壳子，而是当前这轮真正新增的一块逻辑。

它负责：

- 反复调用 executor
- 在 `--dry-run` 下只检查最早一条任务
- 在 `--execute` 下顺序消费 pending 队列
- 处理 `--max-tasks`
- 处理 `--continue-on-failure`
- 汇总本次队列执行结果

因此，`mock_wms_task_runner.py` 属于“功能实现层”，不是“入口桥接层”。

## 4. 为什么不直接把所有逻辑都搬进包目录

当前选择的是“最小改动、最小风险”的方案。

原因如下：

1. 原来的 `scripts/*.py` 已经能工作
2. 这轮主要目标是补齐 `ros2 run` 入口一致性，而不是重构整套 Mock WMS
3. 如果直接把所有实现大规模搬家，会同时改动 CLI、导入路径、测试入口和安装路径，风险更高
4. 用“短包装层 + 公共加载层”的方式，可以在不破坏旧用法的前提下补齐新入口

因此，这轮同时保留了两种调用方式：

```bash
python3 scripts/init_mock_wms_db.py
ros2 run amr_warehouse_sim init_mock_wms_db
```

它们最终会落到同一份脚本实现上。

## 5. 一条实际调用链

下面以：

```bash
ros2 run amr_warehouse_sim init_mock_wms_db
```

为例说明调用链。

### 5.1 第一步：`setup.py` 注册入口

`setup.py` 中声明：

```text
init_mock_wms_db = amr_warehouse_sim.init_mock_wms_db:main
```

这意味着 ROS 2 在执行这个命令时，会进入：

```text
amr_warehouse_sim/init_mock_wms_db.py
```

### 5.2 第二步：包入口文件转发

`amr_warehouse_sim/init_mock_wms_db.py` 本身只做一件事：

- 调用 `_script_entry.load_script_main('init_mock_wms_db.py')`

也就是说，它自己不做数据库逻辑，只负责把执行权交给真正脚本。

### 5.3 第三步：公共加载器找脚本

`amr_warehouse_sim/_script_entry.py` 会：

- 先尝试找源码目录下的 `scripts/init_mock_wms_db.py`
- 如果是安装环境，再尝试找 `share/amr_warehouse_sim/scripts/init_mock_wms_db.py`
- 动态导入这个脚本
- 找到脚本中的 `main()`

### 5.4 第四步：真正实现执行

最后才进入：

```text
scripts/init_mock_wms_db.py
```

这里才会：

- 解析 `--db` / `--db-path`
- 调 `initialize_database()`
- 输出初始化结果

## 6. `mock_wms_executor` 和 `mock_wms_task_runner` 的区别

这两个名字容易混，但职责并不一样。

### 6.1 `mock_wms_executor`

它是“单次执行一条任务”的入口。

职责是：

- 读取最早一条 `pending` task
- 解析目标点
- 检查 Nav2 ready gate
- dry-run 时只记录结果，不发 goal
- execute 时才发 `/navigate_to_pose`
- 把状态写回 SQLite

其中：

- `amr_warehouse_sim/mock_wms_executor.py`
  是包入口壳
- `scripts/run_mock_wms_executor.py`
  是真正执行器实现

### 6.2 `mock_wms_task_runner`

它是“顺序跑队列”的上层控制器。

职责是：

- 连续调用 executor
- 按顺序消费 pending 队列
- 决定遇到失败时是否停止
- 统计本次执行了多少条、成功多少条、失败多少条

所以可以这样理解：

```text
mock_wms_executor
= 处理一条任务

mock_wms_task_runner
= 多次调用 executor 来处理整个队列
```

## 7. 为什么测试文件也跟着变多

新增入口以后，测试自然也要分层补齐。

### 7.1 入口测试

`test/integration/test_mock_wms_cli_entrypoints.py`

它主要验证：

- 这些新模块能不能正常 import
- `main(['--help'])` 能不能跑通
- `python -m amr_warehouse_sim.mock_wms_task_runner --help` 能不能工作

这类测试测的是“入口桥接层是否接通”，不是导航逻辑本身。

### 7.2 executor 合约测试

`test/integration/test_mock_wms_executor_contract.py`

它主要验证：

- 没有 pending task 时怎么返回
- target 非法时怎么回写状态
- ready gate 不满足时是否保持 `pending`
- dry-run 是否不会进入 `running`
- execute 是否会在 ready 后真正推进状态

这类测试测的是“单条任务状态机”。

### 7.3 task runner 合约测试

`test/integration/test_mock_wms_task_runner.py`

它主要验证：

- dry-run 是否只检查一条
- execute 是否能顺序消费多条任务
- ready gate 超时时是否停止
- 失败时默认是否停止
- `continue-on-failure` 时是否继续后续任务

这类测试测的是“队列控制逻辑”。

## 8. 一句话总结

如果只看文件数量，很容易觉得：

- 为什么突然多了这么多 Python 文件
- 为什么有些文件看起来只有几行，好像很多余

更准确的理解应该是：

- 短文件大多是为了把已有脚本接进 `ros2 run` 和包级测试体系的入口包装层
- `_script_entry.py` 是公共桥接工具
- 真正的执行逻辑主要仍在 `scripts/*.py`
- `mock_wms_task_runner.py` 才是这轮新增的主要功能实现

因此，这批文件“数量变多”并不等于“业务逻辑被重复写了很多遍”；更多是在补齐包入口、安装路径兼容和测试可调用性。

## 9. 当前边界

这份说明只解释当前主线的 CLI / 入口桥接结构。

它不代表：

- 已经引入完整 WMS 调度系统
- 已经改写 Nav2 主链路
- 已经把历史 `future_extensions` 逻辑整包接回主线

截至当前主线，更准确的说法仍然是：

- 保留 `navigation.launch.py` + `config/nav2_params.yaml` 作为 V2 稳定基线
- 在此基础上补齐最小 Mock WMS 数据层、单次 executor 和顺序 task runner 的主线入口
- 用最小改动让这些入口既能 `python3 scripts/...`，也能 `ros2 run amr_warehouse_sim ...`
