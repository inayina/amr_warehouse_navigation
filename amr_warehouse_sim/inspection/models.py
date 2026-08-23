from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f'{field_name} must not be empty.')


class ObservationQuality(str, Enum):
    PASS = 'pass'
    STALE = 'stale'
    INCOMPLETE = 'incomplete'
    INVALID = 'invalid'


class FindingOutcome(str, Enum):
    NORMAL = 'normal'
    ANOMALOUS = 'anomalous'


class FindingSeverity(str, Enum):
    WARNING = 'warning'


@dataclass(frozen=True)
class InspectionItem:
    """One deterministic P0 inspection item, independent of a vendor API."""

    item_id: str
    kind: str
    maximum_value: float

    def __post_init__(self) -> None:
        _require_non_empty(self.item_id, 'item_id')
        _require_non_empty(self.kind, 'kind')
        if not isfinite(self.maximum_value):
            raise ValueError('maximum_value must be finite.')


@dataclass(frozen=True)
class InspectionPoint:
    point_id: str
    frame_id: str
    x: float
    y: float
    yaw: float
    maximum_observation_age_ms: int
    item: InspectionItem

    def __post_init__(self) -> None:
        _require_non_empty(self.point_id, 'point_id')
        _require_non_empty(self.frame_id, 'frame_id')
        if not all(isfinite(value) for value in (self.x, self.y, self.yaw)):
            raise ValueError('point pose values must be finite.')
        if self.maximum_observation_age_ms < 0:
            raise ValueError('maximum_observation_age_ms must not be negative.')


@dataclass(frozen=True)
class InspectionTask:
    """P0 business intent; it intentionally contains no assignment/execution state."""

    task_id: str
    route_id: str
    priority: str
    point: InspectionPoint

    def __post_init__(self) -> None:
        _require_non_empty(self.task_id, 'task_id')
        _require_non_empty(self.route_id, 'route_id')
        _require_non_empty(self.priority, 'priority')


@dataclass(frozen=True)
class MockObservation:
    observation_id: str
    item_id: str
    robot_id: str
    point_id: str
    sensor_id: str
    frame_id: str
    captured_at_ms: int
    received_at_ms: int
    value: float
    calibration_version: str = 'mock-calibration-v1'
    complete: bool = True
    source: str = 'mock'

    def __post_init__(self) -> None:
        _require_non_empty(self.observation_id, 'observation_id')
        _require_non_empty(self.item_id, 'item_id')
        _require_non_empty(self.robot_id, 'robot_id')
        _require_non_empty(self.point_id, 'point_id')
        _require_non_empty(self.sensor_id, 'sensor_id')
        _require_non_empty(self.frame_id, 'frame_id')
        _require_non_empty(self.calibration_version, 'calibration_version')
        _require_non_empty(self.source, 'source')


@dataclass(frozen=True)
class QualityResult:
    quality: ObservationQuality
    reason: str

    @property
    def passed(self) -> bool:
        return self.quality is ObservationQuality.PASS


@dataclass(frozen=True)
class InspectionFinding:
    finding_id: str
    outcome: FindingOutcome
    reason: str
    severity: FindingSeverity | None = None


@dataclass(frozen=True)
class EvaluationResult:
    observation_id: str
    measured_value: float
    maximum_value: float
    evaluator_id: str
    evaluator_version: str
    evaluated_at_ms: int
    finding: InspectionFinding


@dataclass(frozen=True)
class EvidenceReference:
    uri: str
    sha256: str

    def __post_init__(self) -> None:
        _require_non_empty(self.uri, 'uri')
        if len(self.sha256) != 64 or any(
            character not in '0123456789abcdefABCDEF' for character in self.sha256
        ):
            raise ValueError('sha256 must contain exactly 64 hexadecimal characters.')


@dataclass(frozen=True)
class PointAttemptSnapshot:
    attempt_id: str
    attempt_number: int
    point_id: str
    execution_phase: str
    navigation_succeeded: bool
    arrival_accepted: bool
    stabilization_succeeded: bool
    observation: MockObservation | None
    quality_result: QualityResult | None
    evaluation_result: EvaluationResult | None
    evidence_reference: EvidenceReference | None
    reason: str | None


@dataclass(frozen=True)
class InspectionRunSnapshot:
    run_id: str
    task_id: str
    robot_id: str
    point_id: str
    execution_phase: str
    attempts: tuple[PointAttemptSnapshot, ...]

    @property
    def current_attempt(self) -> PointAttemptSnapshot:
        return self.attempts[-1]

    @property
    def succeeded(self) -> bool:
        return self.execution_phase == 'succeeded'
