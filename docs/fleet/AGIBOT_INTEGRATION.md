# Agibot D1 MaxPro Vendor Integration

审计与实现日期：`2026-08-23`

状态：**experimental / opt-in / state-only / process-boundary**。官方 C++ high-level SDK 与本仓 read-only probe 已完成 x86 compile/link/loader 验证；mock JSONL IPC 与 Fleet heartbeat mapping 已验证。没有官方 simulator、没有 D1 MaxPro 真机连接、没有发送控制命令。

## 1. Purpose

本实验验证第三种 vendor architecture：即使外部接口不是 ROS 2/DDS，而是 proprietary C++ SDK + vendor TCP transport，Fleet 仍只消费稳定的 liveness event。

```text
D1 MaxPro
  ↓ vendor network
official C++ high-level SDK
  ↓ Robot API
C++ state probe
  ↓ stdout JSONL
Python AgibotStateAdapter
  ↓ record_heartbeat(recover_offline=False)
RobotRegistry
```

它不是 D1 MaxPro task execution、navigation integration 或 production IPC。与 DR02/Unitree substitution experiment 一样，默认仍使用 `robot_02`；三家不同时运行，实验结果应使用不同 SQLite 文件。

## 2. Official SDK audit

事实源：[`AgibotTech/Agibot_D1_MaxPro`](https://github.com/AgibotTech/Agibot_D1_MaxPro/tree/7828aef8238388c11267e56d5e44bac9f6dd2eb4)，commit `7828aef8238388c11267e56d5e44bac9f6dd2eb4`。

固定本地审计 checkout：`vendor_audit/agibot-audit/`（被 `.gitignore` 排除，不 vendoring 到本仓历史）。

| Audit item | Current official checkout finding |
| --- | --- |
| Language | C++ only；官方 README 明确暂不支持其他语言。 |
| Recommended platform | Ubuntu 20.04 x86；Mac/Windows unsupported。 |
| Supplied architectures | `x86/` 与 `arm64/` 均包含 high-level SDK artifact。 |
| High-level ROS requirement | 不要求 ROS1。 |
| Low-level ROS requirement | 要求 ROS1；通过 low-level topics 获取/控制 joint，本轮不使用。 |
| Header | `include/high_level_base.h`：compile-time structs、abstract `Robot` declarations、`createQuadruped()` factory declaration。 |
| Library | `build/libhigh_level_remote_tcp_client.so`：prebuilt vendor implementation；x86 artifact 是 ELF 64-bit x86-64 shared object。 |
| Demo | `src/high_level_remote_tcp_client_test.cpp`：展示 factory/init/getters/control calls。 |
| Build script | `g++ ... -Lbuild -Iinclude -lhigh_level_remote_tcp_client -lcrypto -Wl,-rpath=build`。 |
| High-level transport | 官方 SDK 获取文档明确为 TCP；实现封装在 `.so`。 |
| Simulator | 当前官方仓库没有可独立运行的 physics simulator。 |

### 2.1 Version / firmware constraint

官方明确 SDK 与本体 firmware/protocol 必须匹配。当前 checkout 目录名为 `high_level_remote_client_209`，版本兼容表包含 `v2.0.9`；但 README/ChangeLog 的可见更新记录只写到 `v2.0.7`。因此本仓只 pin commit 和 artifact path，不把目录名冒充为 runtime-confirmed SDK version。

上真机前必须：

1. 在机器人读取 `linx/active/versions.json`；
2. 对照官方 firmware/SDK compatibility table；
3. 必要时联系 vendor 获取严格匹配的 SDK artifact；
4. 运行 getter 后再读取 `GetSdkVersion()` 作为 runtime evidence。

### 2.2 Network topology

| Connection | Official robot IP |
| --- | --- |
| Wi-Fi | `192.168.12.1` |
| Ethernet（recommended） | `192.168.144.3` |
| Type-C | `192.168.55.1` |

当前文档明确 high-level SDK 使用 TCP；当前 public header/demo 没有暴露 IP/port parameter，prebuilt `.so` 中可见 `192.168.144.3` 与 socket/reconnect implementation strings。端口未在当前 repo 的 high-level public contract 中说明，因此记录为 **NOT DISCLOSED / NOT VERIFIED**，不根据旧资料或文件名猜测。

这不是 DDS：application 不创建 ROS publisher/subscriber，也不配置 RMW/domain/QoS；vendor library 自己拥有 socket、协议 serialization、reconnect/version matching 等实现边界。

## 3. C++ SDK architecture

### 3.1 Actual call chain

```text
state_probe.cpp
→ createQuadruped()
→ std::shared_ptr<Robot>
→ Robot virtual interface from high_level_base.h
→ RobotProxy implementation exported by libhigh_level_remote_tcp_client.so
→ robot->init()
→ vendor TCP/socket/protocol lifecycle inside prebuilt library
→ D1 MaxPro
→ robot->GetRobotStatus()
```

`nm -D -C` confirms `.so` exports `createQuadruped()` and `RobotProxy::init()/GetRobotStatus()/GetOdometry()/GetJointState()` symbols。`strings` 还显示 reconnect、socket 和 client/server version match diagnostics；因为 implementation source 未公开，本仓不进一步声称内部 thread 数量、callback executor 或 exact handshake sequence。

### 3.2 Header / library / linker / loader

- Header 是 compile-time declaration：让 compiler 知道 `Robot` vtable contract、struct layout 和 factory signature；它不是实现。
- `.so` 是 vendor implementation：factory、proxy、network/protocol behavior 和 getter implementation 在这里。
- Linker 在 build 时把 probe 对 `createQuadruped()` 等 symbol 的引用解析到 `libhigh_level_remote_tcp_client.so`，同时按官方脚本链接 OpenSSL Crypto。
- Runtime loader 在进程启动时按 RUNPATH/`LD_LIBRARY_PATH` 查找 `.so`；找不到时，程序会在进入 `main()` 前失败。

官方 build script 使用相对 RUNPATH `build`，只有从适当 working directory 启动才容易解析。本仓 probe CMake 把当前 audited SDK library directory 写入 BUILD_RPATH；这是本地实验 build evidence，不是 portable release packaging。

## 4. Why this is not a ROS2 adapter

官方 high-level SDK 本身不要求 ROS1 或 ROS2。人为增加 ROS 2 bridge 会新增 message design、topic/QoS/domain/RMW 和 bridge lifecycle，却不会消除 C++ SDK/socket/version constraint，反而遮蔽真正的 vendor boundary。

三家的外部接口应该保持真实：

```text
DEEPRobotics: application → ROS 2 topic → DDS → simulator/robot
Unitree:      application → ROS 2/CycloneDDS wire contract → simulator/robot
Agibot:       application → official C++ SDK → vendor TCP protocol → robot
```

内部只统一 normalized liveness semantic，不统一 vendor transport mechanism。

## 5. Selected read-only state mapping

选择 `GetRobotStatus()`：

- 当前 public header 和官方 demo 均实际存在；提示词中的 `GetRobotState()` 不存在。
- 它属于 device status getter，不发 motion/joint/charging/mode command。
- polling 足够表达本轮 experiment，不依赖 undocumented callback thread。
- 返回的 `Robotstate.driver_temperature[12]` 被 probe 故意丢弃；getter 正常返回后只输出一帧 normalized telemetry event。

成功 getter 只映射：

```python
registry.record_heartbeat(
    robot_id,
    recover_offline=False,
)
```

不映射 driver temperature、odometry、joint state、battery、alert、pose、Fleet state、task status 或 execution capability。尤其 OFFLINE + telemetry 仍保持 OFFLINE。

局限：`GetRobotStatus()` 返回 struct 而不是 explicit status code；probe 能确认 `init()` 返回零且 getter 未抛异常，但无法从 public contract 证明数据 freshness。真机验收仍需 timestamp/rate/connection-loss experiment。

## 6. Process / IPC contract

### 6.1 Probe stdout JSONL

每次 read-only getter 正常返回：

```json
{"event":"telemetry","vendor":"agibot","model":"d1_maxpro","source":"GetRobotStatus"}
```

Python parser 必须匹配 `event/vendor/model`；允许向后兼容的 extra fields。malformed JSON、非 object、错误 vendor/model/event 会被计为 rejected line，不更新 heartbeat。

stdout 只承载 JSONL；diagnostics 写 stderr。这个 contract 是 **experimental local process boundary**，不是 authenticated、versioned、backpressured production IPC。

### 6.2 Lifecycle ownership

Python `agibot_state_adapter` 是 child-process owner：

1. fail-fast 校验 probe executable；
2. `Popen` 启动精确 executable，不使用 shell；
3. 逐行读取 stdout；
4. EOF + zero valid telemetry 报明确错误；
5. non-zero child exit 报 exit code 与 accepted/rejected count；
6. Ctrl+C 向精确 child 发送 SIGINT，等待最多 5 秒后才 terminate 该 child。

C++ signal handler 只设置 `sig_atomic_t` stop flag；主循环退出后释放 `shared_ptr<Robot>`。probe 不调用 `StopMove/Getdown/Standup/Move`。官方 demo 的 cleanup 会发送控制命令，因此本轮没有运行官方 demo runtime。

### 6.3 Callback audit

官方 header 有 `FetchAllAlertsAsync(AlertCallback)`，但 callback thread ownership、lifetime、blocking allowance 和 shutdown contract 没有公开 source 证据。若在未知高频 callback 中直接写 SQLite，可能阻塞 vendor I/O thread、放大锁竞争并使 shutdown 不确定。

本轮使用低频 polling；若未来必须使用 callback，应先验证 callback thread，再采用 callback → bounded lightweight queue → worker，而不是在 callback 内直接做 persistence。

## 7. Build and run

官方 SDK checkout 固定在：

```text
vendor_audit/agibot-audit/x86/high_level_remote_client_209
```

独立配置/构建 probe：

```bash
cmake \
  -S vendor_tools/agibot_d1_maxpro \
  -B vendor_audit/agibot-probe-build \
  -DAGIBOT_SDK_ROOT="$PWD/vendor_audit/agibot-audit/x86/high_level_remote_client_209" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build vendor_audit/agibot-probe-build --parallel 4
```

有真实且版本匹配的 D1 MaxPro、完成网络/控制权只读 preflight 后：

```bash
ros2 run amr_warehouse_sim agibot_state_adapter \
  --robot-id robot_02 \
  --fleet-db /path/to/agibot_experiment.db \
  --probe "$PWD/vendor_audit/agibot-probe-build/agibot_d1_maxpro_state_probe"
```

虽然使用 `ros2 run` 启动 Python package console entry，Agibot transport 本身不是 ROS 2；同样可直接运行 Python module。

## 8. Test evidence

| Capability | Evidence |
| --- | --- |
| Import without vendor SDK | PASS |
| JSONL validation | PASS |
| malformed/foreign line ignored | PASS |
| valid event → heartbeat | PASS |
| OFFLINE/task/station/battery unchanged | PASS |
| SQLite persistence | PASS |
| missing probe actionable error | PASS |
| clean EOF before telemetry | PASS |
| child non-zero exit | PASS |
| mock child process contract | PASS |
| DR02/Unitree/Agibot parity | PASS |

Mock child 使用当前 Python executable 输出一帧 JSONL；它只证明 process contract，不证明 official SDK runtime。

## 9. Runtime evidence

### 9.1 Environment

| Item | Measured value |
| --- | --- |
| Host | Ubuntu 24.04.4 LTS, x86_64 |
| Compiler | GCC/G++ 13.3.0 |
| Official recommendation | Ubuntu 20.04 x86 |
| OpenSSL used for link | 3.0.13 |
| Official checkout | `7828aef8238388c11267e56d5e44bac9f6dd2eb4` |

### 9.2 Build / link / loader

- Official `x86/high_level_remote_client_209/build.sh`: **COMPILE/LINK PASS**。
- 本仓 `agibot_d1_maxpro_state_probe`: **CMAKE CONFIGURE + COMPILE/LINK PASS**。
- `file`: x86-64 ELF PIE executable。
- `ldd`: official `.so` 与 `libcrypto.so.3` 均 resolved。
- `--help`: exit code `0`，证明 loader 能在不连接机器人时进入 executable。

### 9.3 Connection / telemetry

| Check | Result |
| --- | --- |
| Official simulator | NOT AVAILABLE in current repo |
| `createQuadruped()` runtime | NOT RUN |
| `robot->init()` | NOT RUN |
| `GetRobotStatus()` against robot | NOT RUN |
| Real JSONL from official SDK | NOT RUN |
| Real SQLite before/after | NOT RUN |
| Real D1 MaxPro | **NOT TESTED** |

没有把 compile/link、mock JSONL 或 loader success 重解释成 robot connection success。

## 10. Limitations

- no real robot、no official simulator；
- no command、no navigation、no task execution；
- no ROS 2 bridge、no ROS1 in AMR workspace；
- no ctypes/pybind11 and no SDK files inside Python package；
- no production-grade IPC authentication/version negotiation/backpressure；
- getter freshness 与 connection-loss behavior 未验证；
- current host 不在官方推荐 OS matrix；
- default probe build contains an absolute local RUNPATH and is local evidence, not redistributable release artifact。

## 11. Fleet boundary result

本轮没有修改 `fleet/execution_context.py`、`fleet/dispatcher.py`、`fleet/haul_executor.py`、`fleet/task_lifecycle.py`、`fleet/robot_state.py` 或 schema。

Agibot 的 `Robot*`、factory、`.so`、TCP/socket、vendor structs 与 firmware version matching 全部停在 vendor-side process；Fleet 只看到 valid normalized telemetry event。这个结果验证的是 liveness seam，不外推到 Agibot navigation/control capability。
