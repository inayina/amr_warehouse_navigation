#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DASHBOARD_REPO_ROOT="${DASHBOARD_REPO_ROOT:-/home/ina/workspace/robot-ops-dashboard}"
DB_PATH="${MOCK_WMS_DB_PATH:-$REPO_ROOT/data/mock_wms.db}"
TASK_POINTS_PATH="${MOCK_WMS_TASK_POINTS_PATH:-$REPO_ROOT/config/task_points.yaml}"

DB_PATH_WAS_PROVIDED=false
TASK_POINTS_PATH_WAS_PROVIDED=false

declare -a FORWARDED_ARGS=()
declare -a TARGETS=()

usage() {
    cat <<EOF
用法：
  $(basename "$0") [选项] [target1 target2 ...]

默认录屏流程：
  1. 使用 AMR 数据库：$DB_PATH
  2. 对接看板仓库：$DASHBOARD_REPO_ROOT
  3. 启动/检查 Mock WMS API、Dashboard backend、Dashboard frontend
  4. 顺序跑四个任务点：
     station_a station_b shelf_1 shelf_2

常用示例：
  ./scripts/run_mock_wms_dashboard_recording_demo.sh
  ./scripts/run_mock_wms_dashboard_recording_demo.sh --skip-launch
  ./scripts/run_mock_wms_dashboard_recording_demo.sh --headless --verbose
  ./scripts/run_mock_wms_dashboard_recording_demo.sh --dashboard-repo /home/ina/workspace/robot-ops-dashboard

本脚本选项：
  --dashboard-repo PATH   看板仓库路径，默认：$DASHBOARD_REPO_ROOT
  --amr-repo PATH         AMR 仓库路径，默认：$REPO_ROOT
  --db PATH               Mock WMS SQLite 数据库，默认：$DB_PATH
  --task-points PATH      task_points.yaml，默认：$TASK_POINTS_PATH
  -h, --help              显示帮助

透传给看板录屏脚本的常用选项：
  --no-clean              不向 AMR visual demo 传 --clean
  --skip-launch           复用已经启动的 navigation.launch.py
  --headless              headless 运行 AMR visual demo
  --verbose               打印 AMR visual demo 详细 ready 状态
  --no-run-demo           只启动/检查 API、Dashboard 和前端，不执行四点任务
  --cleanup-services      脚本退出时关闭本脚本启动的 API / Dashboard / frontend

说明：
  这是 AMR 仓库侧的薄封装。实际编排逻辑在看板仓库的
  scripts/run_amr_dashboard_recording_demo.sh 中。
  默认会重置 $DB_PATH，再创建四个任务点用于录屏。
EOF
}

fail() {
    echo "[dashboard-recording-demo] ERROR: $*" >&2
    exit 1
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dashboard-repo)
                DASHBOARD_REPO_ROOT=$2
                shift 2
                ;;
            --amr-repo)
                REPO_ROOT="$(cd "$2" && pwd)"
                if [[ "$DB_PATH_WAS_PROVIDED" == false ]]; then
                    DB_PATH="$REPO_ROOT/data/mock_wms.db"
                fi
                if [[ "$TASK_POINTS_PATH_WAS_PROVIDED" == false ]]; then
                    TASK_POINTS_PATH="$REPO_ROOT/config/task_points.yaml"
                fi
                shift 2
                ;;
            --db)
                DB_PATH=$2
                DB_PATH_WAS_PROVIDED=true
                shift 2
                ;;
            --task-points)
                TASK_POINTS_PATH=$2
                TASK_POINTS_PATH_WAS_PROVIDED=true
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            --)
                shift
                while [[ $# -gt 0 ]]; do
                    TARGETS+=("$1")
                    shift
                done
                ;;
            -*)
                FORWARDED_ARGS+=("$1")
                shift
                ;;
            *)
                TARGETS+=("$1")
                shift
                ;;
        esac
    done

    if [[ ${#TARGETS[@]} -eq 0 ]]; then
        TARGETS=(station_a station_b shelf_1 shelf_2)
    fi
}

main() {
    parse_args "$@"

    local dashboard_script="$DASHBOARD_REPO_ROOT/scripts/run_amr_dashboard_recording_demo.sh"

    [[ -d "$REPO_ROOT" ]] || fail "AMR 仓库不存在：$REPO_ROOT"
    [[ -f "$TASK_POINTS_PATH" ]] || fail "未找到 task points 文件：$TASK_POINTS_PATH"
    [[ -x "$REPO_ROOT/scripts/run_mock_wms_visual_demo.sh" ]] || \
        fail "未找到 AMR visual demo 脚本：$REPO_ROOT/scripts/run_mock_wms_visual_demo.sh"
    [[ -x "$dashboard_script" ]] || \
        fail "未找到看板录屏脚本：$dashboard_script"

    echo "[dashboard-recording-demo] AMR 仓库：$REPO_ROOT"
    echo "[dashboard-recording-demo] 看板仓库：$DASHBOARD_REPO_ROOT"
    echo "[dashboard-recording-demo] 数据库：$DB_PATH"
    echo "[dashboard-recording-demo] 任务点：${TARGETS[*]}"

    AMR_REPO_ROOT="$REPO_ROOT" \
    AMR_DB_PATH="$DB_PATH" \
    TASK_POINTS_PATH="$TASK_POINTS_PATH" \
    bash "$dashboard_script" \
        --amr-repo "$REPO_ROOT" \
        --db "$DB_PATH" \
        --task-points "$TASK_POINTS_PATH" \
        "${FORWARDED_ARGS[@]}" \
        "${TARGETS[@]}"
}

main "$@"
