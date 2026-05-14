#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from .mock_wms_db_common import default_db_path, list_tasks

DISPLAY_COLUMNS = (
    'id',
    'task_name',
    'target_name',
    'x',
    'y',
    'yaw',
    'status',
    'status_reason',
    'created_at',
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='List tasks from the minimal SQLite database for the V3.0 Mock WMS data layer.'
    )
    parser.add_argument(
        '--db',
        '--db-path',
        type=Path,
        default=default_db_path(),
        dest='db_path',
        help='SQLite database path. Defaults to data/mock_wms.db under the repo root.',
    )
    return parser


def _format_value(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, float):
        text = f'{value:.3f}'
        return text.rstrip('0').rstrip('.') if '.' in text else text
    return str(value)


def render_task_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return 'No mock WMS tasks found.'

    widths = {column: len(column) for column in DISPLAY_COLUMNS}
    rendered_rows: list[dict[str, str]] = []

    for row in rows:
        rendered = {column: _format_value(row[column]) for column in DISPLAY_COLUMNS}
        rendered_rows.append(rendered)
        for column, value in rendered.items():
            widths[column] = max(widths[column], len(value))

    header = '  '.join(column.ljust(widths[column]) for column in DISPLAY_COLUMNS)
    separator = '  '.join('-' * widths[column] for column in DISPLAY_COLUMNS)
    lines = [header, separator]

    for row in rendered_rows:
        lines.append('  '.join(row[column].ljust(widths[column]) for column in DISPLAY_COLUMNS))

    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = list_tasks(args.db_path)
    print(render_task_table(rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
