#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from .mock_wms_db_common import (
    create_task,
    default_db_path,
    default_task_points_path,
    resolve_target_pose,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Create one pending Mock WMS task from config/task_points.yaml.'
    )
    parser.add_argument(
        '--target',
        required=True,
        help='Target name in config/task_points.yaml. dock_a is accepted as a compatibility alias.',
    )
    parser.add_argument(
        '--task-name',
        default=None,
        help='Optional explicit task_name. Defaults to a generated mock-task-* value.',
    )
    parser.add_argument(
        '--db',
        '--db-path',
        type=Path,
        default=default_db_path(),
        dest='db_path',
        help='SQLite database path. Defaults to data/mock_wms.db under the repo root.',
    )
    parser.add_argument(
        '--task-points',
        type=Path,
        default=default_task_points_path(),
        help='Task point YAML path. Defaults to config/task_points.yaml under the repo root.',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    resolved_target_name, _ = resolve_target_pose(args.target, args.task_points)
    task = create_task(
        requested_target_name=args.target,
        db_path=args.db_path,
        task_points_path=args.task_points,
        task_name=args.task_name,
    )

    if args.target != resolved_target_name:
        print(
            f'[mock_wms_db] Requested target "{args.target}" resolved to '
            f'"{resolved_target_name}" from config/task_points.yaml.'
        )

    print(
        '[mock_wms_db] Created pending task: '
        f'id={task["id"]}, task_name={task["task_name"]}, target_name={task["target_name"]}, '
        f'frame_id={task["frame_id"]}, x={task["x"]}, y={task["y"]}, yaw={task["yaw"]}, '
        f'status={task["status"]}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
