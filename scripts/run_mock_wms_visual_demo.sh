#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$(cd "$REPO_ROOT/../.." && pwd)"

PKG_NAME="amr_warehouse_sim"
DB_PATH="/tmp/mock_wms_visual_demo.db"
TASK_POINTS_PATH="$REPO_ROOT/config/task_points.yaml"
LAUNCH_LOG="/tmp/mock_wms_visual_demo_launch.log"

USE_GZ_GUI=true
USE_RVIZ=true
SKIP_LAUNCH=false
CLEAN_PROCESSES=false
VERBOSE=false

INITIAL_POSE_WAIT_SEC=30
READY_TIMEOUT_SEC=60
PRECHECK_TIMEOUT_SEC=90
READY_POLL_INTERVAL_SEC=2
NAVIGATION_TIMEOUT_SEC=180
MAX_TASKS=""

declare -a TARGETS=()

usage() {
    cat <<EOF
用法：
  $(basename "$0") [选项] [target1 target2 ...]

默认目标点：
  station_a station_b

常用示例：
  ./scripts/run_mock_wms_visual_demo.sh --clean
  ./scripts/run_mock_wms_visual_demo.sh --skip-launch station_a
  ./scripts/run_mock_wms_visual_demo.sh --headless --clean --ready-timeout 90
  ./scripts/run_mock_wms_visual_demo.sh --clean --verbose

选项：
  --clean                    启动前清理旧 Gazebo / Nav2 / RViz 相关进程
  --skip-launch              复用当前已运行的 navigation.launch.py，会话
  --headless                 以 headless 方式启动，等价于 use_gz_gui:=false use_rviz:=false
  --verbose                  打印等待 localization / ready 的详细状态
  --db PATH                  SQLite 演示数据库路径，默认：$DB_PATH
  --task-points PATH         task_points.yaml 路径，默认：$TASK_POINTS_PATH
  --launch-log PATH          launch 日志文件，默认：$LAUNCH_LOG
  --initial-pose-wait SEC    publish_initial_pose 等待订阅者秒数，默认：$INITIAL_POSE_WAIT_SEC
  --ready-timeout SEC        task runner 的 execute ready-timeout，默认：$READY_TIMEOUT_SEC
  --precheck-timeout SEC     脚本等待 Nav2 ready 的总秒数，默认：$PRECHECK_TIMEOUT_SEC
  --ready-poll-interval SEC  轮询 ready 状态间隔，默认：$READY_POLL_INTERVAL_SEC
  --navigation-timeout SEC   每个 goal 的导航超时，默认：$NAVIGATION_TIMEOUT_SEC
  --max-tasks N              task runner 最大消费任务数，默认：目标点数量
  -h, --help                 显示帮助

说明：
  1. 这个脚本会自动：
     启动 navigation.launch.py -> publish_initial_pose -> 等待 ready ->
     初始化数据库 -> 创建任务 -> 执行 mock_wms_task_runner -> 打印最终状态
  2. 如果不传目标点，默认创建 station_a 和 station_b。
  3. 如果当前已有导航会话，建议配合 --skip-launch 或 --clean 使用，避免重复启动。
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "缺少依赖命令: $1"
        exit 1
    fi
}

timestamp_utc() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
    echo "[visual-demo $(timestamp_utc)] $*"
}

verbose_log() {
    if [[ "$VERBOSE" == true ]]; then
        log "$*"
    fi
}

tail_launch_log() {
    if [[ -f "$LAUNCH_LOG" ]]; then
        echo
        echo "[visual-demo] 最近 launch 日志："
        tail -n 40 "$LAUNCH_LOG" || true
    fi
}

on_error() {
    echo
    echo "[visual-demo] 演示脚本执行失败。"
    tail_launch_log
}

source_ros_env() {
    local nounset_was_on=false
    case $- in
        *u*)
            nounset_was_on=true
            set +u
            ;;
    esac

    # shellcheck disable=SC1091
    source /opt/ros/jazzy/setup.bash
    # shellcheck disable=SC1091
    source "$WORKSPACE/install/setup.bash"

    if [[ "$nounset_was_on" == true ]]; then
        set -u
    fi
}

run_ros_cmd() {
    source_ros_env
    "$@"
}

get_lifecycle_state() {
    local node_name=$1
    local output
    output="$(run_ros_cmd ros2 lifecycle get "$node_name" 2>&1 || true)"

    case "$output" in
        *"active ["*)
            echo "active"
            ;;
        *"inactive ["*)
            echo "inactive"
            ;;
        *"unconfigured ["*)
            echo "unconfigured"
            ;;
        *"configuring ["*)
            echo "configuring"
            ;;
        *"activating ["*)
            echo "activating"
            ;;
        *"deactivating ["*)
            echo "deactivating"
            ;;
        *"cleaningup ["*)
            echo "cleaningup"
            ;;
        *"shuttingdown ["*)
            echo "shuttingdown"
            ;;
        *"finalized ["*)
            echo "finalized"
            ;;
        *"Node not found"*)
            echo "not-found"
            ;;
        "")
            echo "unknown"
            ;;
        *)
            echo "$output" | tail -n 1
            ;;
    esac
}

cleanup_processes() {
    log "清理旧 Gazebo / Nav2 / RViz / bridge 相关进程..."
    pkill -f "ros2 launch $PKG_NAME navigation.launch.py" 2>/dev/null || true
    pkill -f "gz sim" 2>/dev/null || true
    pkill -f parameter_bridge 2>/dev/null || true
    pkill -f scan_to_scan_filter_chain 2>/dev/null || true
    pkill -f odom_tf_node 2>/dev/null || true
    pkill -f robot_state_publisher 2>/dev/null || true
    pkill -f rviz2 2>/dev/null || true
    pkill -f map_server 2>/dev/null || true
    pkill -f amcl 2>/dev/null || true
    pkill -f controller_server 2>/dev/null || true
    pkill -f planner_server 2>/dev/null || true
    pkill -f smoother_server 2>/dev/null || true
    pkill -f behavior_server 2>/dev/null || true
    pkill -f bt_navigator 2>/dev/null || true
    pkill -f waypoint_follower 2>/dev/null || true
    pkill -f velocity_smoother 2>/dev/null || true
    pkill -f lifecycle_manager 2>/dev/null || true
    sleep 2
}

launch_already_running() {
    pgrep -f "ros2 launch $PKG_NAME navigation.launch.py" >/dev/null 2>&1
}

start_navigation_launch() {
    if launch_already_running; then
        echo "检测到现有 navigation.launch.py 会话正在运行。"
        echo "请改用 --skip-launch 复用当前会话，或使用 --clean 先清理旧进程。"
        exit 1
    fi

    : > "$LAUNCH_LOG"
    log "后台启动 navigation.launch.py，日志写入 $LAUNCH_LOG"
    nohup bash -lc "
        source /opt/ros/jazzy/setup.bash
        source '$WORKSPACE/install/setup.bash'
        ros2 launch $PKG_NAME navigation.launch.py use_gz_gui:=$USE_GZ_GUI use_rviz:=$USE_RVIZ
    " >"$LAUNCH_LOG" 2>&1 &
    local launch_pid=$!
    log "navigation.launch.py 已启动，PID=$launch_pid"
    sleep 3
}

publish_initial_pose() {
    log "发布 start_zone initial pose"
    run_ros_cmd ros2 run "$PKG_NAME" publish_initial_pose \
        --preset start_zone \
        --wait-for-subscribers "$INITIAL_POSE_WAIT_SEC"
}

lifecycle_node_active() {
    local node_name=$1
    [[ "$(get_lifecycle_state "$node_name")" == "active" ]]
}

all_lifecycle_nodes_active() {
    local node_name
    for node_name in /map_server /amcl /planner_server /controller_server /bt_navigator; do
        if ! lifecycle_node_active "$node_name"; then
            return 1
        fi
    done
    return 0
}

map_to_odom_available() {
    local output
    output="$(run_ros_cmd timeout 4s ros2 run tf2_ros tf2_echo map odom 2>&1 || true)"
    [[ "$output" == *"Translation:"* ]]
}

action_server_available() {
    local output
    output="$(run_ros_cmd ros2 action info /navigate_to_pose 2>&1 || true)"
    [[ "$output" =~ Action\ servers:\ [1-9] ]]
}

print_wait_status() {
    if [[ "$VERBOSE" != true ]]; then
        return 0
    fi

    local phase=$1
    local map_server_state amcl_state planner_state controller_state bt_state
    local tf_state action_state

    map_server_state="$(get_lifecycle_state /map_server)"
    amcl_state="$(get_lifecycle_state /amcl)"
    planner_state="$(get_lifecycle_state /planner_server)"
    controller_state="$(get_lifecycle_state /controller_server)"
    bt_state="$(get_lifecycle_state /bt_navigator)"

    if map_to_odom_available; then
        tf_state="ready"
    else
        tf_state="waiting"
    fi

    if action_server_available; then
        action_state="ready"
    else
        action_state="waiting"
    fi

    verbose_log "$phase: /map_server=$map_server_state /amcl=$amcl_state /planner_server=$planner_state /controller_server=$controller_state /bt_navigator=$bt_state map->odom=$tf_state navigate_to_pose=$action_state"
}

print_ready_snapshot() {
    local node_name
    echo "[visual-demo] 当前 ready 快照："
    for node_name in /map_server /amcl /planner_server /controller_server /bt_navigator; do
        run_ros_cmd ros2 lifecycle get "$node_name" 2>&1 || true
    done
    run_ros_cmd ros2 action info /navigate_to_pose 2>&1 || true
}

wait_for_localization_ready() {
    local deadline attempts=0
    deadline=$((SECONDS + PRECHECK_TIMEOUT_SEC))

    while (( SECONDS < deadline )); do
        attempts=$((attempts + 1))
        if lifecycle_node_active /map_server && lifecycle_node_active /amcl; then
            log "Localization 已就绪（/map_server、/amcl active，尝试 $attempts 次）"
            return 0
        fi

        print_wait_status "等待 localization"
        sleep "$READY_POLL_INTERVAL_SEC"
    done

    echo "Localization 在 ${PRECHECK_TIMEOUT_SEC}s 内仍未进入 ready 状态。"
    print_ready_snapshot
    tail_launch_log
    return 1
}

wait_for_nav2_ready() {
    local deadline attempts=0
    deadline=$((SECONDS + PRECHECK_TIMEOUT_SEC))

    while (( SECONDS < deadline )); do
        attempts=$((attempts + 1))
        if all_lifecycle_nodes_active && map_to_odom_available && action_server_available; then
            log "Nav2 ready gate 已满足（尝试 $attempts 次）"
            return 0
        fi

        print_wait_status "等待 Nav2 ready"
        if (( attempts % 3 == 0 )); then
            log "ready 尚未满足，补发一次 initial pose"
            publish_initial_pose || true
        fi

        sleep "$READY_POLL_INTERVAL_SEC"
    done

    echo "Nav2 在 ${PRECHECK_TIMEOUT_SEC}s 内仍未进入 ready 状态。"
    print_ready_snapshot
    tail_launch_log
    return 1
}

reset_demo_db() {
    log "重置演示数据库：$DB_PATH"
    rm -f "$DB_PATH"
    run_ros_cmd ros2 run "$PKG_NAME" init_mock_wms_db --db "$DB_PATH"
}

create_demo_tasks() {
    local target
    for target in "${TARGETS[@]}"; do
        log "创建 pending task: $target"
        run_ros_cmd ros2 run "$PKG_NAME" create_mock_task \
            --db "$DB_PATH" \
            --task-points "$TASK_POINTS_PATH" \
            --target "$target" \
            --task-name "demo-$target"
    done
}

list_demo_tasks() {
    run_ros_cmd ros2 run "$PKG_NAME" list_mock_tasks --db "$DB_PATH"
}

run_task_runner() {
    local resolved_max_tasks=$MAX_TASKS
    if [[ -z "$resolved_max_tasks" ]]; then
        resolved_max_tasks=${#TARGETS[@]}
    fi

    log "执行 mock_wms_task_runner，目标任务数=$resolved_max_tasks"
    run_ros_cmd ros2 run "$PKG_NAME" mock_wms_task_runner \
        --db "$DB_PATH" \
        --task-points "$TASK_POINTS_PATH" \
        --execute \
        --max-tasks "$resolved_max_tasks" \
        --ready-timeout "$READY_TIMEOUT_SEC" \
        --ready-poll-interval "$READY_POLL_INTERVAL_SEC" \
        --navigation-timeout "$NAVIGATION_TIMEOUT_SEC"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --clean)
                CLEAN_PROCESSES=true
                shift
                ;;
            --skip-launch)
                SKIP_LAUNCH=true
                shift
                ;;
            --headless)
                USE_GZ_GUI=false
                USE_RVIZ=false
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --db)
                DB_PATH=$2
                shift 2
                ;;
            --task-points)
                TASK_POINTS_PATH=$2
                shift 2
                ;;
            --launch-log)
                LAUNCH_LOG=$2
                shift 2
                ;;
            --initial-pose-wait)
                INITIAL_POSE_WAIT_SEC=$2
                shift 2
                ;;
            --ready-timeout)
                READY_TIMEOUT_SEC=$2
                shift 2
                ;;
            --precheck-timeout)
                PRECHECK_TIMEOUT_SEC=$2
                shift 2
                ;;
            --ready-poll-interval)
                READY_POLL_INTERVAL_SEC=$2
                shift 2
                ;;
            --navigation-timeout)
                NAVIGATION_TIMEOUT_SEC=$2
                shift 2
                ;;
            --max-tasks)
                MAX_TASKS=$2
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                TARGETS+=("$1")
                shift
                ;;
        esac
    done
}

main() {
    parse_args "$@"
    trap on_error ERR

    if [[ ${#TARGETS[@]} -eq 0 ]]; then
        TARGETS=(station_a station_b)
    fi

    require_cmd bash
    require_cmd nohup
    require_cmd ros2
    require_cmd timeout

    if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
        echo "未找到 /opt/ros/jazzy/setup.bash，请先安装 ROS 2 Jazzy。"
        exit 1
    fi

    if [[ ! -f "$WORKSPACE/install/setup.bash" ]]; then
        echo "未找到 $WORKSPACE/install/setup.bash。请先在工作空间执行 colcon build。"
        exit 1
    fi

    if [[ ! -f "$TASK_POINTS_PATH" ]]; then
        echo "未找到 task points 文件：$TASK_POINTS_PATH"
        exit 1
    fi

    log "工作空间：$WORKSPACE"
    log "数据库：$DB_PATH"
    log "目标点：${TARGETS[*]}"

    if [[ "$CLEAN_PROCESSES" == true ]]; then
        cleanup_processes
    fi

    if [[ "$SKIP_LAUNCH" == false ]]; then
        start_navigation_launch
    else
        log "复用当前 navigation.launch.py 会话"
    fi

    wait_for_localization_ready
    publish_initial_pose
    wait_for_nav2_ready

    reset_demo_db
    create_demo_tasks

    log "执行前任务列表："
    list_demo_tasks

    run_task_runner

    log "执行后任务列表："
    list_demo_tasks

    echo
    echo "演示流程完成。"
    echo "如果需要查看 launch 日志：tail -f $LAUNCH_LOG"
    if [[ "$SKIP_LAUNCH" == false ]]; then
        echo "如果需要手动结束 GUI 会话：pkill -f \"ros2 launch $PKG_NAME navigation.launch.py\""
    fi
}

main "$@"
