from __future__ import annotations

import math
from pathlib import Path

from amr_warehouse_sim.mock_wms_db_common import default_task_points_path, load_task_points

from .robot_state import FleetError


class StationNotFoundError(FleetError):
    """Raised when a station name is missing from task_points.yaml."""


def _station_xy(
    task_points: dict[str, dict[str, object]],
    station_name: str,
) -> tuple[float, float]:
    if station_name not in task_points:
        raise StationNotFoundError(
            f'Station {station_name!r} was not found in task_points.yaml.'
        )

    point = task_points[station_name]
    x = point.get('x')
    y = point.get('y')
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise StationNotFoundError(
            f'Station {station_name!r} does not have numeric x/y coordinates.'
        )
    return float(x), float(y)


def static_station_distance(
    origin_station: str | None,
    target_station: str,
    *,
    task_points_path: Path | None = None,
    task_points: dict[str, dict[str, object]] | None = None,
) -> float:
    points = task_points or load_task_points(task_points_path or default_task_points_path())
    if origin_station is None:
        raise StationNotFoundError('Origin station is required for static distance.')

    origin_x, origin_y = _station_xy(points, origin_station)
    target_x, target_y = _station_xy(points, target_station)
    return math.hypot(target_x - origin_x, target_y - origin_y)
