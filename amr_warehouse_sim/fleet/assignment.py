from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from .registry import initialize_fleet_database, now_timestamp


class AssignmentStatus(str, Enum):
    ASSIGNED = 'assigned'
    EXECUTING = 'executing'
    RELEASED = 'released'
    CANCELED = 'canceled'
    COMPLETED = 'completed'
    FAILED = 'failed'


ASSIGNMENT_STATUSES = tuple(status.value for status in AssignmentStatus)
ACTIVE_ASSIGNMENT_STATUSES = frozenset(
    {AssignmentStatus.ASSIGNED, AssignmentStatus.EXECUTING}
)

ASSIGNMENT_COLUMNS = (
    'id',
    'task_id',
    'robot_id',
    'pickup_station',
    'cost',
    'dispatch_reason',
    'status',
    'assigned_at',
    'updated_at',
)


@dataclass(frozen=True)
class AssignmentRecord:
    id: int
    task_id: int
    robot_id: str
    pickup_station: str
    cost: float
    dispatch_reason: str
    status: AssignmentStatus
    assigned_at: str
    updated_at: str

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_ASSIGNMENT_STATUSES

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['status'] = self.status.value
        return payload


def _select_assignment_columns() -> str:
    return ',\n                '.join(ASSIGNMENT_COLUMNS)


def _row_to_assignment(row: sqlite3.Row) -> AssignmentRecord:
    return AssignmentRecord(
        id=int(row['id']),
        task_id=int(row['task_id']),
        robot_id=str(row['robot_id']),
        pickup_station=str(row['pickup_station']),
        cost=float(row['cost']),
        dispatch_reason=str(row['dispatch_reason']),
        status=AssignmentStatus(str(row['status'])),
        assigned_at=str(row['assigned_at']),
        updated_at=str(row['updated_at']),
    )


def initialize_assignments_table(db_path: Path | None = None) -> Path:
    db_file = initialize_fleet_database(db_path)
    allowed_statuses = ', '.join(f"'{status}'" for status in ASSIGNMENT_STATUSES)
    create_table_sql = f'''
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        robot_id TEXT NOT NULL,
        pickup_station TEXT NOT NULL,
        cost REAL NOT NULL,
        dispatch_reason TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ({allowed_statuses})),
        assigned_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    '''

    with sqlite3.connect(db_file) as connection:
        connection.execute(create_table_sql)
        connection.execute(
            'CREATE INDEX IF NOT EXISTS idx_assignments_task_id '
            'ON assignments(task_id)'
        )
        connection.execute(
            'CREATE INDEX IF NOT EXISTS idx_assignments_robot_status '
            'ON assignments(robot_id, status)'
        )
        connection.commit()

    return db_file


def persist_assignment(assignment: AssignmentRecord, db_path: Path | None = None) -> AssignmentRecord:
    db_file = initialize_assignments_table(db_path)
    with sqlite3.connect(db_file) as connection:
        if assignment.id == 0:
            cursor = connection.execute(
                '''
                INSERT INTO assignments (
                    task_id,
                    robot_id,
                    pickup_station,
                    cost,
                    dispatch_reason,
                    status,
                    assigned_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    assignment.task_id,
                    assignment.robot_id,
                    assignment.pickup_station,
                    assignment.cost,
                    assignment.dispatch_reason,
                    assignment.status.value,
                    assignment.assigned_at,
                    assignment.updated_at,
                ),
            )
            assignment_id = int(cursor.lastrowid)
        else:
            connection.execute(
                '''
                UPDATE assignments
                SET robot_id = ?,
                    pickup_station = ?,
                    cost = ?,
                    dispatch_reason = ?,
                    status = ?,
                    assigned_at = ?,
                    updated_at = ?
                WHERE id = ?
                ''',
                (
                    assignment.robot_id,
                    assignment.pickup_station,
                    assignment.cost,
                    assignment.dispatch_reason,
                    assignment.status.value,
                    assignment.assigned_at,
                    assignment.updated_at,
                    assignment.id,
                ),
            )
            assignment_id = assignment.id
        connection.commit()

    return _fetch_assignment_by_id(db_file, assignment_id)


def _fetch_assignment_by_id(db_path: Path, assignment_id: int) -> AssignmentRecord:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            f'''
            SELECT
                {_select_assignment_columns()}
            FROM assignments
            WHERE id = ?
            ''',
            (assignment_id,),
        ).fetchone()
    if row is None:
        raise KeyError(f'Assignment id={assignment_id} was not found.')
    return _row_to_assignment(row)


def load_assignments_from_db(db_path: Path | None = None) -> dict[int, AssignmentRecord]:
    db_file = initialize_assignments_table(db_path)
    with sqlite3.connect(db_file) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f'''
            SELECT
                {_select_assignment_columns()}
            FROM assignments
            ORDER BY id ASC
            '''
        ).fetchall()
    return {int(row['task_id']): _row_to_assignment(row) for row in rows}
