from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite


class InspectionRunStatus(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELED = 'canceled'


class InspectionPointStatus(str, Enum):
    PENDING = 'pending'
    NAVIGATING = 'navigating'
    ARRIVED = 'arrived'
    STABILIZING = 'stabilizing'
    ACQUIRING = 'acquiring'
    VALIDATING = 'validating'
    EVALUATING = 'evaluating'
    SUCCEEDED = 'succeeded'
    NAVIGATION_FAILED = 'navigation_failed'
    ACQUISITION_FAILED = 'acquisition_failed'
    DATA_INVALID = 'data_invalid'
    EVALUATION_FAILED = 'evaluation_failed'


class InspectionFindingLevel(str, Enum):
    PASS = 'pass'
    WARNING = 'warning'
    CRITICAL = 'critical'


class InspectionFaultCode(str, Enum):
    NAVIGATION_FAILED = 'navigation_failed'
    CAMERA_UNAVAILABLE = 'camera_unavailable'
    IMAGE_TIMEOUT = 'image_timeout'
    DATA_INVALID = 'data_invalid'
    EVALUATION_FAILED = 'evaluation_failed'
    ROBOT_NOT_READY = 'robot_not_ready'


_POINT_TRANSITIONS = {
    InspectionPointStatus.PENDING: {InspectionPointStatus.NAVIGATING},
    InspectionPointStatus.NAVIGATING: {
        InspectionPointStatus.ARRIVED,
        InspectionPointStatus.NAVIGATION_FAILED,
    },
    InspectionPointStatus.ARRIVED: {InspectionPointStatus.STABILIZING},
    InspectionPointStatus.STABILIZING: {InspectionPointStatus.ACQUIRING},
    InspectionPointStatus.ACQUIRING: {
        InspectionPointStatus.VALIDATING,
        InspectionPointStatus.ACQUISITION_FAILED,
    },
    InspectionPointStatus.VALIDATING: {
        InspectionPointStatus.EVALUATING,
        InspectionPointStatus.DATA_INVALID,
    },
    InspectionPointStatus.EVALUATING: {
        InspectionPointStatus.SUCCEEDED,
        InspectionPointStatus.EVALUATION_FAILED,
    },
}


@dataclass(frozen=True)
class InspectionPointSpec:
    point_id: str
    sequence: int
    frame_id: str
    x: float
    y: float
    yaw: float
    image_topic: str
    stabilization_sec: float
    red_ratio_threshold: float

    def __post_init__(self) -> None:
        if not self.point_id.strip() or not self.frame_id.strip():
            raise ValueError('Inspection point_id and frame_id must be non-empty.')
        if self.sequence < 1:
            raise ValueError('Inspection point sequence must be positive.')
        if not all(isfinite(value) for value in (self.x, self.y, self.yaw)):
            raise ValueError('Inspection point pose must contain finite values.')
        if not self.image_topic.startswith('/'):
            raise ValueError('Inspection image_topic must be an absolute ROS topic.')
        if self.stabilization_sec < 0.0:
            raise ValueError('stabilization_sec must not be negative.')
        if not 0.0 <= self.red_ratio_threshold <= 1.0:
            raise ValueError('red_ratio_threshold must be between 0 and 1.')

    @property
    def pose(self) -> dict[str, object]:
        return {
            'frame_id': self.frame_id,
            'x': self.x,
            'y': self.y,
            'yaw': self.yaw,
        }


@dataclass
class PointExecutionState:
    point_id: str
    status: InspectionPointStatus = InspectionPointStatus.PENDING
    transitions: list[dict[str, object]] = field(default_factory=list)

    def transition(
        self,
        status: InspectionPointStatus,
        *,
        at_ns: int,
        reason: str | None = None,
    ) -> None:
        allowed = _POINT_TRANSITIONS.get(self.status, set())
        if status not in allowed:
            raise ValueError(
                f'Invalid inspection point transition: {self.status.value} -> '
                f'{status.value}.'
            )
        self.status = status
        event: dict[str, object] = {'status': status.value, 'at_ns': at_ns}
        if reason is not None:
            event['reason'] = reason
        self.transitions.append(event)


@dataclass(frozen=True)
class ImageObservation:
    run_id: str
    point_id: str
    robot_id: str
    captured_at_ns: int
    received_at_ns: int
    acquisition_started_at_ns: int
    image_topic: str
    image_width: int
    image_height: int
    encoding: str
    artifact_ref: str
    red_ratio: float

    def to_dict(self) -> dict[str, object]:
        return {
            'run_id': self.run_id,
            'point_id': self.point_id,
            'robot_id': self.robot_id,
            'captured_at_ns': self.captured_at_ns,
            'received_at_ns': self.received_at_ns,
            'acquisition_started_at_ns': self.acquisition_started_at_ns,
            'image_topic': self.image_topic,
            'image_width': self.image_width,
            'image_height': self.image_height,
            'encoding': self.encoding,
            'artifact_ref': self.artifact_ref,
            'red_ratio': self.red_ratio,
        }
