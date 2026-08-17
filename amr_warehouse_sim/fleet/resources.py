from __future__ import annotations

import sqlite3
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from .registry import initialize_fleet_database, now_timestamp, parse_timestamp
from .robot_state import FleetError

DEFAULT_RESOURCE_TIMEOUT_SEC = 120.0
DEFAULT_DEMO_RESOURCES = (
    'pickup_station_a',
    'narrow_aisle_1',
)


class ResourceAcquireResult(str, Enum):
    ACQUIRED = 'acquired'
    ALREADY_OWNED = 'already_owned'
    WAITING = 'waiting'


class ResourceLockError(FleetError):
    """Base error for resource lock operations."""


class ResourceNotFoundError(ResourceLockError):
    """Raised when a resource id is unknown."""


class ResourceOwnershipError(ResourceLockError):
    """Raised when a robot cannot release a resource it does not own."""


@dataclass(frozen=True)
class ResourceRecord:
    resource_id: str
    owner_robot_id: str | None
    acquired_at: str | None
    updated_at: str

    @property
    def is_free(self) -> bool:
        return self.owner_robot_id is None

    def to_dict(self) -> dict[str, object]:
        return {
            'resource_id': self.resource_id,
            'owner_robot_id': self.owner_robot_id,
            'acquired_at': self.acquired_at,
            'updated_at': self.updated_at,
            'state': 'FREE' if self.is_free else f'OWNED({self.owner_robot_id})',
        }


@dataclass(frozen=True)
class ResourceEvent:
    timestamp: str
    event: str
    resource_id: str
    robot_id: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            'timestamp': self.timestamp,
            'event': self.event,
            'resource_id': self.resource_id,
            'robot_id': self.robot_id,
            'reason': self.reason,
        }


def initialize_resources_table(db_path: Path | None = None) -> Path:
    db_file = initialize_fleet_database(db_path)
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS resources (
        resource_id TEXT PRIMARY KEY,
        owner_robot_id TEXT,
        acquired_at TEXT,
        updated_at TEXT NOT NULL
    )
    '''
    with sqlite3.connect(db_file) as connection:
        connection.execute(create_table_sql)
        connection.commit()
    return db_file


def _persist_resource(resource: ResourceRecord, db_path: Path | None) -> None:
    if db_path is None:
        return
    db_file = initialize_resources_table(db_path)
    with sqlite3.connect(db_file) as connection:
        connection.execute(
            '''
            INSERT INTO resources (
                resource_id,
                owner_robot_id,
                acquired_at,
                updated_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(resource_id) DO UPDATE SET
                owner_robot_id = excluded.owner_robot_id,
                acquired_at = excluded.acquired_at,
                updated_at = excluded.updated_at
            ''',
            (
                resource.resource_id,
                resource.owner_robot_id,
                resource.acquired_at,
                resource.updated_at,
            ),
        )
        connection.commit()


class ResourceLockManager:
    """Minimal logical resource ownership with FIFO waiting and timeout."""

    def __init__(
        self,
        *,
        resource_ids: tuple[str, ...] = DEFAULT_DEMO_RESOURCES,
        db_path: Path | None = None,
        event_sink: list[ResourceEvent] | None = None,
        ownership_timeout_sec: float = DEFAULT_RESOURCE_TIMEOUT_SEC,
    ):
        self._db_path = Path(db_path) if db_path is not None else None
        self._event_sink = event_sink if event_sink is not None else []
        self._ownership_timeout_sec = max(ownership_timeout_sec, 0.0)
        timestamp = now_timestamp()
        self._resources: dict[str, ResourceRecord] = {
            resource_id: ResourceRecord(
                resource_id=resource_id,
                owner_robot_id=None,
                acquired_at=None,
                updated_at=timestamp,
            )
            for resource_id in resource_ids
        }
        self._wait_queues: dict[str, deque[str]] = {
            resource_id: deque() for resource_id in resource_ids
        }

    @property
    def resources(self) -> list[ResourceRecord]:
        return [self._resources[resource_id] for resource_id in sorted(self._resources)]

    def _emit(
        self,
        event: str,
        *,
        resource_id: str,
        robot_id: str | None = None,
        reason: str | None = None,
        timestamp: str | None = None,
    ) -> ResourceEvent:
        fleet_event = ResourceEvent(
            timestamp=timestamp or now_timestamp(),
            event=event,
            resource_id=resource_id,
            robot_id=robot_id,
            reason=reason,
        )
        self._event_sink.append(fleet_event)
        return fleet_event

    def _get_resource(self, resource_id: str) -> ResourceRecord:
        resource = self._resources.get(resource_id)
        if resource is None:
            raise ResourceNotFoundError(f'Resource {resource_id!r} was not found.')
        return resource

    def _replace_resource(self, resource: ResourceRecord) -> ResourceRecord:
        self._resources[resource.resource_id] = resource
        _persist_resource(resource, self._db_path)
        return resource

    def is_waiting(self, resource_id: str, robot_id: str) -> bool:
        queue = self._wait_queues.get(resource_id)
        if queue is None:
            raise ResourceNotFoundError(f'Resource {resource_id!r} was not found.')
        return robot_id in queue

    def list_waiters(self, resource_id: str) -> list[str]:
        queue = self._wait_queues.get(resource_id)
        if queue is None:
            raise ResourceNotFoundError(f'Resource {resource_id!r} was not found.')
        return list(queue)

    def get_resource(self, resource_id: str) -> ResourceRecord:
        return self._get_resource(resource_id)

    def ownership_age_sec(self, resource_id: str, *, now: datetime) -> float | None:
        resource = self._get_resource(resource_id)
        if resource.acquired_at is None:
            return None
        acquired = parse_timestamp(resource.acquired_at)
        return max((now - acquired).total_seconds(), 0.0)

    def acquire(
        self,
        resource_id: str,
        robot_id: str,
        *,
        timestamp: str | None = None,
    ) -> ResourceAcquireResult:
        resource = self._get_resource(resource_id)
        ts = timestamp or now_timestamp()

        if resource.owner_robot_id == robot_id:
            return ResourceAcquireResult.ALREADY_OWNED

        if resource.is_free:
            updated = ResourceRecord(
                resource_id=resource_id,
                owner_robot_id=robot_id,
                acquired_at=ts,
                updated_at=ts,
            )
            self._replace_resource(updated)
            self._emit(
                'RESOURCE_ACQUIRED',
                resource_id=resource_id,
                robot_id=robot_id,
                reason='resource was free',
                timestamp=ts,
            )
            return ResourceAcquireResult.ACQUIRED

        queue = self._wait_queues[resource_id]
        if robot_id not in queue:
            queue.append(robot_id)
            self._emit(
                'RESOURCE_WAITING',
                resource_id=resource_id,
                robot_id=robot_id,
                reason=f'owned by {resource.owner_robot_id}',
                timestamp=ts,
            )
        return ResourceAcquireResult.WAITING

    def acquire_ordered(
        self,
        robot_id: str,
        resource_ids: list[str],
        *,
        timestamp: str | None = None,
    ) -> list[tuple[str, ResourceAcquireResult]]:
        """Acquire multiple resources in sorted order to avoid lock-order deadlocks."""
        ordered = sorted(set(resource_ids))
        return [
            (resource_id, self.acquire(resource_id, robot_id, timestamp=timestamp))
            for resource_id in ordered
        ]

    def release(
        self,
        resource_id: str,
        robot_id: str,
        *,
        timestamp: str | None = None,
    ) -> ResourceRecord:
        resource = self._get_resource(resource_id)
        if resource.owner_robot_id != robot_id:
            raise ResourceOwnershipError(
                f'Robot {robot_id!r} does not own resource {resource_id!r}.'
            )

        ts = timestamp or now_timestamp()
        freed = ResourceRecord(
            resource_id=resource_id,
            owner_robot_id=None,
            acquired_at=None,
            updated_at=ts,
        )
        self._replace_resource(freed)
        self._emit(
            'RESOURCE_RELEASED',
            resource_id=resource_id,
            robot_id=robot_id,
            reason='explicit release',
            timestamp=ts,
        )

        queue = self._wait_queues[resource_id]
        while queue:
            next_robot = queue.popleft()
            result = self.acquire(resource_id, next_robot, timestamp=ts)
            if result == ResourceAcquireResult.ACQUIRED:
                break
            if result == ResourceAcquireResult.WAITING:
                queue.appendleft(next_robot)
                break

        return self._get_resource(resource_id)

    def sweep_timeouts(
        self,
        *,
        now: datetime,
        timeout_sec: float | None = None,
    ) -> list[str]:
        from datetime import timezone

        limit = self._ownership_timeout_sec if timeout_sec is None else max(timeout_sec, 0.0)
        released: list[str] = []
        timestamp = (
            now.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace('+00:00', 'Z')
        )

        for resource in list(self.resources):
            if resource.owner_robot_id is None or resource.acquired_at is None:
                continue
            age = self.ownership_age_sec(resource.resource_id, now=now)
            if age is None or age <= limit:
                continue
            owner = resource.owner_robot_id
            self.release(resource.resource_id, owner, timestamp=timestamp)
            self._emit(
                'RESOURCE_TIMEOUT',
                resource_id=resource.resource_id,
                robot_id=owner,
                reason=f'ownership exceeded {limit:.1f}s',
                timestamp=timestamp,
            )
            released.append(resource.resource_id)
        return released
