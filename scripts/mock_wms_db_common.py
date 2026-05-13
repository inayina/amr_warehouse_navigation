from __future__ import annotations

import ast
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

TASK_STATUSES = (
    'pending',
    'running',
    'succeeded',
    'failed',
    'canceled',
)

SUPPORTED_V3_TARGET_NAMES = {
    'candidate_dock_a',
    'dock_a',
    'station_a',
    'station_b',
    'shelf_1',
    'shelf_2',
}

TARGET_NAME_FALLBACKS = {
    'candidate_dock_a': 'dock_a',
    'dock_a': 'candidate_dock_a',
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return repo_root() / 'data' / 'mock_wms.db'


def default_task_points_path() -> Path:
    return repo_root() / 'config' / 'task_points.yaml'


def _parse_scalar(value: str):
    value = value.strip()
    if value == 'TBD':
        return value
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def load_task_points(task_points_path: Path | None = None) -> dict[str, dict[str, object]]:
    path = Path(task_points_path or default_task_points_path())
    if not path.is_file():
        raise FileNotFoundError(f'Task points file not found: {path}')

    points: dict[str, dict[str, object]] = {}
    current_point: str | None = None

    for raw_line in path.read_text(encoding='utf-8').splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        if not raw_line.startswith(' '):
            if not stripped.endswith(':'):
                raise ValueError(f'Invalid top-level YAML line: {raw_line}')
            current_point = stripped[:-1]
            points[current_point] = {}
            continue

        if current_point is None or ':' not in stripped:
            raise ValueError(f'Invalid nested YAML line: {raw_line}')

        key, value = stripped.split(':', 1)
        points[current_point][key.strip()] = _parse_scalar(value)

    return points


def resolve_target_name(
    requested_target_name: str,
    task_points: dict[str, dict[str, object]],
) -> str:
    if requested_target_name in task_points:
        return requested_target_name

    fallback_name = TARGET_NAME_FALLBACKS.get(requested_target_name)
    if fallback_name and fallback_name in task_points:
        return fallback_name

    raise KeyError(
        f'Target "{requested_target_name}" was not found in {default_task_points_path().name}.'
    )


def resolve_target_pose(
    requested_target_name: str,
    task_points_path: Path | None = None,
) -> tuple[str, dict[str, object]]:
    task_points = load_task_points(task_points_path)
    resolved_target_name = resolve_target_name(requested_target_name, task_points)
    if resolved_target_name not in SUPPORTED_V3_TARGET_NAMES:
        raise ValueError(
            'V3.0 Mock WMS currently accepts validated task targets: '
            'candidate_dock_a / dock_a, station_a, station_b, shelf_1, shelf_2.'
        )
    point = task_points[resolved_target_name]

    frame_id = point.get('frame_id')
    if frame_id != 'map':
        raise ValueError(
            f'Target "{resolved_target_name}" must use frame_id "map", got "{frame_id}".'
        )

    pose: dict[str, object] = {
        'frame_id': frame_id,
        'x': point.get('x'),
        'y': point.get('y'),
        'yaw': point.get('yaw'),
    }

    for field_name in ('x', 'y', 'yaw'):
        value = pose[field_name]
        if value == 'TBD':
            raise ValueError(
                f'Target "{resolved_target_name}" is not ready for Mock WMS tasks because '
                f'field "{field_name}" is still TBD.'
            )
        if not isinstance(value, (int, float)):
            raise ValueError(
                f'Target "{resolved_target_name}" field "{field_name}" must be numeric, got {value!r}.'
            )
        pose[field_name] = float(value)

    return resolved_target_name, pose


def now_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace('+00:00', 'Z')
    )


def build_task_name(target_name: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return f'mock-task-{target_name}-{timestamp}'


def initialize_database(db_path: Path | None = None) -> Path:
    db_file = Path(db_path or default_db_path())
    db_file.parent.mkdir(parents=True, exist_ok=True)

    allowed_statuses = ', '.join(f"'{status}'" for status in TASK_STATUSES)
    create_table_sql = f'''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT NOT NULL,
        target_name TEXT NOT NULL,
        frame_id TEXT NOT NULL,
        x REAL NOT NULL,
        y REAL NOT NULL,
        yaw REAL NOT NULL,
        status TEXT NOT NULL CHECK (status IN ({allowed_statuses})),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    '''

    with sqlite3.connect(db_file) as connection:
        connection.execute(create_table_sql)
        connection.execute(
            'CREATE INDEX IF NOT EXISTS idx_tasks_status_created_at '
            'ON tasks(status, created_at)'
        )
        connection.commit()

    return db_file


def create_task(
    requested_target_name: str,
    db_path: Path | None = None,
    task_points_path: Path | None = None,
    task_name: str | None = None,
) -> dict[str, object]:
    db_file = initialize_database(db_path)
    resolved_target_name, pose = resolve_target_pose(requested_target_name, task_points_path)
    final_task_name = task_name or build_task_name(resolved_target_name)
    timestamp = now_timestamp()

    with sqlite3.connect(db_file) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            '''
            INSERT INTO tasks (
                task_name,
                target_name,
                frame_id,
                x,
                y,
                yaw,
                status,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                final_task_name,
                resolved_target_name,
                pose['frame_id'],
                pose['x'],
                pose['y'],
                pose['yaw'],
                'pending',
                timestamp,
                timestamp,
            ),
        )
        task_id = cursor.lastrowid
        row = connection.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        connection.commit()

    return dict(row) if row is not None else {}


def list_tasks(db_path: Path | None = None) -> list[dict[str, object]]:
    db_file = Path(db_path or default_db_path())
    if not db_file.is_file():
        raise FileNotFoundError(
            f'Mock WMS database not found: {db_file}. Run init_mock_wms_db.py first.'
        )

    with sqlite3.connect(db_file) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            '''
            SELECT
                id,
                task_name,
                target_name,
                frame_id,
                x,
                y,
                yaw,
                status,
                created_at,
                updated_at
            FROM tasks
            ORDER BY id ASC
            '''
        ).fetchall()

    return [dict(row) for row in rows]
