from datetime import datetime, timedelta, timezone

import pytest

from amr_warehouse_sim.fleet import (
    ResourceAcquireResult,
    ResourceLockManager,
    ResourceOwnershipError,
)


FIXED_NOW = datetime(2026, 8, 17, 9, 0, 0, tzinfo=timezone.utc)
LATER = FIXED_NOW + timedelta(seconds=5)
TIMEOUT_NOW = FIXED_NOW + timedelta(seconds=121)


def _manager() -> tuple[ResourceLockManager, list]:
    events = []
    manager = ResourceLockManager(event_sink=events)
    return manager, events


def test_scenario_f_second_robot_waits_for_owned_resource():
    manager, events = _manager()

    first = manager.acquire('narrow_aisle_1', 'robot_01', timestamp='2026-08-17T09:00:00Z')
    second = manager.acquire('narrow_aisle_1', 'robot_02', timestamp='2026-08-17T09:00:01Z')

    assert first == ResourceAcquireResult.ACQUIRED
    assert second == ResourceAcquireResult.WAITING
    assert manager.get_resource('narrow_aisle_1').owner_robot_id == 'robot_01'
    assert manager.is_waiting('narrow_aisle_1', 'robot_02')
    assert manager.list_waiters('narrow_aisle_1') == ['robot_02']
    assert [event.event for event in events] == [
        'RESOURCE_ACQUIRED',
        'RESOURCE_WAITING',
    ]


def test_scenario_g_release_grants_waiting_robot():
    manager, events = _manager()
    manager.acquire('narrow_aisle_1', 'robot_01', timestamp='2026-08-17T09:00:00Z')
    manager.acquire('narrow_aisle_1', 'robot_02', timestamp='2026-08-17T09:00:01Z')

    manager.release('narrow_aisle_1', 'robot_01', timestamp='2026-08-17T09:00:02Z')

    assert manager.get_resource('narrow_aisle_1').owner_robot_id == 'robot_02'
    assert manager.is_waiting('narrow_aisle_1', 'robot_02') is False
    assert 'RESOURCE_RELEASED' in [event.event for event in events]
    assert events[-1].event == 'RESOURCE_ACQUIRED'
    assert events[-1].robot_id == 'robot_02'


def test_acquire_ordered_uses_lexicographic_lock_ordering():
    manager, _ = _manager()
    results = manager.acquire_ordered(
        'robot_01',
        ['narrow_aisle_1', 'pickup_station_a'],
        timestamp='2026-08-17T09:00:00Z',
    )

    assert [resource_id for resource_id, _ in results] == [
        'narrow_aisle_1',
        'pickup_station_a',
    ]
    assert all(result == ResourceAcquireResult.ACQUIRED for _, result in results)


def test_release_by_non_owner_is_rejected():
    manager, _ = _manager()
    manager.acquire('pickup_station_a', 'robot_01')

    with pytest.raises(ResourceOwnershipError):
        manager.release('pickup_station_a', 'robot_02')


def test_ownership_timeout_releases_and_grants_next_waiter():
    manager, events = _manager()
    manager.acquire(
        'narrow_aisle_1',
        'robot_01',
        timestamp='2026-08-17T09:00:00Z',
    )
    manager.acquire(
        'narrow_aisle_1',
        'robot_02',
        timestamp='2026-08-17T09:00:01Z',
    )

    released = manager.sweep_timeouts(now=TIMEOUT_NOW, timeout_sec=120.0)

    assert released == ['narrow_aisle_1']
    assert manager.get_resource('narrow_aisle_1').owner_robot_id == 'robot_02'
    assert 'RESOURCE_TIMEOUT' in [event.event for event in events]


def test_already_owned_returns_without_duplicating_waiter():
    manager, _ = _manager()
    manager.acquire('narrow_aisle_1', 'robot_01')

    again = manager.acquire('narrow_aisle_1', 'robot_01')

    assert again == ResourceAcquireResult.ALREADY_OWNED
    assert manager.list_waiters('narrow_aisle_1') == []
