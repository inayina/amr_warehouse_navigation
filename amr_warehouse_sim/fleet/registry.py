from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .robot_state import (
    ACTIVE_TASK_STATES,
    DISPATCHABLE_STATES,
    InvalidRobotTransitionError,
    RobotActiveTaskConflictError,
    RobotNotAvailableError,
    RobotNotFoundError,
    RobotState,
    assert_transition_allowed,
)

DEFAULT_ROBOT_IDS = ('robot_01', 'robot_02')
DEFAULT_STATION = 'start_zone'
DEFAULT_BATTERY = 100.0
DEFAULT_HEARTBEAT_TIMEOUT_SEC = 30.0

ROBOT_COLUMNS = (
    'robot_id',
    'state',
    'current_task_id',
    'current_station',
    'last_heartbeat',
    'battery',
    'updated_at',
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_fleet_db_path() -> Path:
    return repo_root() / 'data' / 'fleet.db'


def now_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace('+00:00', 'Z')
    )


def parse_timestamp(value: str) -> datetime:
    normalized = value.replace('Z', '+00:00')
    return datetime.fromisoformat(normalized)


@dataclass(frozen=True)
class RobotRecord:
    robot_id: str
    state: RobotState
    current_task_id: int | None
    current_station: str | None
    last_heartbeat: str | None
    battery: float
    updated_at: str

    @property
    def has_active_task(self) -> bool:
        return self.current_task_id is not None and self.state in ACTIVE_TASK_STATES

    @property
    def is_dispatchable(self) -> bool:
        return (
            self.state in DISPATCHABLE_STATES
            and self.current_task_id is None
            and self.state != RobotState.OFFLINE
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['state'] = self.state.value
        return payload


def _select_robot_columns() -> str:
    return ',\n                '.join(ROBOT_COLUMNS)


def _row_to_robot(row: sqlite3.Row) -> RobotRecord:
    raw_task_id = row['current_task_id']
    return RobotRecord(
        robot_id=str(row['robot_id']),
        state=RobotState(str(row['state'])),
        current_task_id=None if raw_task_id is None else int(raw_task_id),
        current_station=row['current_station'],
        last_heartbeat=row['last_heartbeat'],
        battery=float(row['battery']),
        updated_at=str(row['updated_at']),
    )


def initialize_fleet_database(db_path: Path | None = None) -> Path:
    db_file = Path(db_path or default_fleet_db_path())
    parent = db_file.parent
    if str(parent) not in ('', '.'):
        parent.mkdir(parents=True, exist_ok=True)

    allowed_states = ', '.join(f"'{state.value}'" for state in RobotState)
    create_table_sql = f'''
    CREATE TABLE IF NOT EXISTS robots (
        robot_id TEXT PRIMARY KEY,
        state TEXT NOT NULL CHECK (state IN ({allowed_states})),
        current_task_id INTEGER,
        current_station TEXT,
        last_heartbeat TEXT,
        battery REAL NOT NULL,
        updated_at TEXT NOT NULL
    )
    '''

    with sqlite3.connect(db_file) as connection:
        connection.execute(create_table_sql)
        connection.commit()

    return db_file


def _fetch_robot_row(connection: sqlite3.Connection, robot_id: str) -> sqlite3.Row | None:
    connection.row_factory = sqlite3.Row
    return connection.execute(
        f'''
        SELECT
            {_select_robot_columns()}
        FROM robots
        WHERE robot_id = ?
        ''',
        (robot_id,),
    ).fetchone()


def load_robots_from_db(db_path: Path | None = None) -> dict[str, RobotRecord]:
    db_file = initialize_fleet_database(db_path)
    with sqlite3.connect(db_file) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f'''
            SELECT
                {_select_robot_columns()}
            FROM robots
            ORDER BY robot_id ASC
            '''
        ).fetchall()

    return {row['robot_id']: _row_to_robot(row) for row in rows}


def persist_robot_to_db(robot: RobotRecord, db_path: Path | None = None) -> RobotRecord:
    db_file = initialize_fleet_database(db_path)
    with sqlite3.connect(db_file) as connection:
        connection.execute(
            '''
            INSERT INTO robots (
                robot_id,
                state,
                current_task_id,
                current_station,
                last_heartbeat,
                battery,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(robot_id) DO UPDATE SET
                state = excluded.state,
                current_task_id = excluded.current_task_id,
                current_station = excluded.current_station,
                last_heartbeat = excluded.last_heartbeat,
                battery = excluded.battery,
                updated_at = excluded.updated_at
            ''',
            (
                robot.robot_id,
                robot.state.value,
                robot.current_task_id,
                robot.current_station,
                robot.last_heartbeat,
                robot.battery,
                robot.updated_at,
            ),
        )
        connection.commit()
    return robot


def build_default_robot(
    robot_id: str,
    *,
    timestamp: str | None = None,
    current_station: str = DEFAULT_STATION,
    battery: float = DEFAULT_BATTERY,
) -> RobotRecord:
    ts = timestamp or now_timestamp()
    return RobotRecord(
        robot_id=robot_id,
        state=RobotState.IDLE,
        current_task_id=None,
        current_station=current_station,
        last_heartbeat=ts,
        battery=battery,
        updated_at=ts,
    )


def seed_default_robots(
    *,
    timestamp: str | None = None,
    robot_ids: Iterable[str] = DEFAULT_ROBOT_IDS,
) -> dict[str, RobotRecord]:
    robots = {
        robot_id: build_default_robot(robot_id, timestamp=timestamp)
        for robot_id in robot_ids
    }
    return robots


def is_heartbeat_valid(
    robot: RobotRecord,
    *,
    now: datetime,
    timeout_sec: float = DEFAULT_HEARTBEAT_TIMEOUT_SEC,
) -> bool:
    if robot.last_heartbeat is None:
        return False
    last_seen = parse_timestamp(robot.last_heartbeat)
    age_sec = (now - last_seen).total_seconds()
    return age_sec <= max(timeout_sec, 0.0)


class RobotRegistry:
    """In-memory robot registry with optional SQLite persistence."""

    def __init__(
        self,
        robots: dict[str, RobotRecord] | None = None,
        *,
        db_path: Path | None = None,
        auto_seed: bool = True,
    ):
        self._db_path = Path(db_path) if db_path is not None else None

        if robots is not None:
            self._robots = dict(robots)
        elif self._db_path is not None:
            loaded = load_robots_from_db(self._db_path)
            self._robots = loaded if loaded else (seed_default_robots() if auto_seed else {})
            if not loaded and auto_seed:
                self.persist_all()
        else:
            self._robots = seed_default_robots() if auto_seed else {}

    @property
    def db_path(self) -> Path | None:
        return self._db_path

    def list_robots(self) -> list[RobotRecord]:
        return [self._robots[robot_id] for robot_id in sorted(self._robots)]

    def get_robot(self, robot_id: str) -> RobotRecord:
        robot = self._robots.get(robot_id)
        if robot is None:
            raise RobotNotFoundError(f'Robot {robot_id!r} was not found.')
        return robot

    def upsert_robot(self, robot: RobotRecord) -> RobotRecord:
        self._robots[robot.robot_id] = robot
        if self._db_path is not None:
            persist_robot_to_db(robot, self._db_path)
        return robot

    def persist_all(self) -> None:
        if self._db_path is None:
            return
        initialize_fleet_database(self._db_path)
        for robot in self.list_robots():
            persist_robot_to_db(robot, self._db_path)

    def _transition(
        self,
        robot_id: str,
        target_state: RobotState,
        *,
        current_task_id=...,
        current_station=...,
        last_heartbeat=...,
        battery=...,
    ) -> RobotRecord:
        robot = self.get_robot(robot_id)
        assert_transition_allowed(robot.state, target_state)

        updated = RobotRecord(
            robot_id=robot.robot_id,
            state=target_state,
            current_task_id=(
                robot.current_task_id if current_task_id is ... else current_task_id
            ),
            current_station=(
                robot.current_station if current_station is ... else current_station
            ),
            last_heartbeat=(
                robot.last_heartbeat if last_heartbeat is ... else last_heartbeat
            ),
            battery=robot.battery if battery is ... else battery,
            updated_at=now_timestamp(),
        )
        return self.upsert_robot(updated)

    def record_heartbeat(
        self,
        robot_id: str,
        *,
        timestamp: str | None = None,
        current_station: str | None = None,
        battery: float | None = None,
        recover_offline: bool = True,
    ) -> RobotRecord:
        """Record liveness, optionally applying the existing OFFLINE recovery policy.

        Vendor telemetry adapters must pass ``recover_offline=False``: receiving a
        transport frame proves that the data path is alive, but does not establish
        a Fleet business state such as IDLE.
        """
        robot = self.get_robot(robot_id)
        ts = timestamp or now_timestamp()
        updated = RobotRecord(
            robot_id=robot.robot_id,
            state=robot.state,
            current_task_id=robot.current_task_id,
            current_station=current_station if current_station is not None else robot.current_station,
            last_heartbeat=ts,
            battery=robot.battery if battery is None else battery,
            updated_at=ts,
        )
        if recover_offline and robot.state == RobotState.OFFLINE:
            if robot.current_task_id is not None:
                return self.upsert_robot(updated)
            assert_transition_allowed(robot.state, RobotState.IDLE)
            updated = RobotRecord(
                robot_id=updated.robot_id,
                state=RobotState.IDLE,
                current_task_id=updated.current_task_id,
                current_station=updated.current_station,
                last_heartbeat=updated.last_heartbeat,
                battery=updated.battery,
                updated_at=updated.updated_at,
            )
        return self.upsert_robot(updated)

    def can_accept_task(
        self,
        robot_id: str,
        *,
        now: datetime | None = None,
        heartbeat_timeout_sec: float = DEFAULT_HEARTBEAT_TIMEOUT_SEC,
    ) -> bool:
        try:
            robot = self.get_robot(robot_id)
        except RobotNotFoundError:
            return False

        if robot.state == RobotState.OFFLINE:
            return False
        if robot.has_active_task:
            return False
        if robot.state not in DISPATCHABLE_STATES:
            return False
        if now is None:
            return robot.last_heartbeat is not None
        return is_heartbeat_valid(
            robot,
            now=now,
            timeout_sec=heartbeat_timeout_sec,
        )

    def assign_task(self, robot_id: str, task_id: int) -> RobotRecord:
        robot = self.get_robot(robot_id)

        if robot.state == RobotState.OFFLINE:
            raise RobotNotAvailableError(
                f'Robot {robot_id!r} is OFFLINE and cannot accept task {task_id}.'
            )
        if robot.has_active_task:
            raise RobotActiveTaskConflictError(
                f'Robot {robot_id!r} already holds active task {robot.current_task_id}.'
            )
        if robot.state not in DISPATCHABLE_STATES:
            raise RobotNotAvailableError(
                f'Robot {robot_id!r} in state {robot.state.value} cannot accept task {task_id}.'
            )

        return self._transition(
            robot_id,
            RobotState.ASSIGNED,
            current_task_id=int(task_id),
        )

    def mark_busy(self, robot_id: str) -> RobotRecord:
        robot = self.get_robot(robot_id)
        if robot.current_task_id is None:
            raise RobotNotAvailableError(
                f'Robot {robot_id!r} cannot become BUSY without an assigned task.'
            )
        return self._transition(robot_id, RobotState.BUSY)

    def release_task(self, robot_id: str) -> RobotRecord:
        robot = self.get_robot(robot_id)
        if robot.state not in ACTIVE_TASK_STATES:
            raise InvalidRobotTransitionError(
                f'Robot {robot_id!r} in state {robot.state.value} has no active task to release.'
            )
        return self._transition(
            robot_id,
            RobotState.IDLE,
            current_task_id=None,
        )

    def mark_offline(self, robot_id: str) -> RobotRecord:
        robot = self.get_robot(robot_id)
        if robot.state == RobotState.OFFLINE:
            return robot
        return self._transition(robot_id, RobotState.OFFLINE)

    def mark_error(self, robot_id: str) -> RobotRecord:
        self.get_robot(robot_id)
        return self._transition(robot_id, RobotState.ERROR)

    def set_current_station(self, robot_id: str, station: str) -> RobotRecord:
        robot = self.get_robot(robot_id)
        updated = RobotRecord(
            robot_id=robot.robot_id,
            state=robot.state,
            current_task_id=robot.current_task_id,
            current_station=station,
            last_heartbeat=robot.last_heartbeat,
            battery=robot.battery,
            updated_at=now_timestamp(),
        )
        return self.upsert_robot(updated)

    def recover_to_idle(self, robot_id: str) -> RobotRecord:
        robot = self.get_robot(robot_id)
        if robot.current_task_id is not None:
            raise RobotActiveTaskConflictError(
                f'Robot {robot_id!r} still references task {robot.current_task_id}; '
                'release or reassign before recovery.'
            )
        return self._transition(robot_id, RobotState.IDLE, current_task_id=None)
