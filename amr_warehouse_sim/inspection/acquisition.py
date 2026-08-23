from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import InspectionPoint, MockObservation


class InspectionAcquisitionError(RuntimeError):
    """Raised when an inspection action cannot produce an observation."""


@dataclass(frozen=True)
class AcquisitionRequest:
    run_id: str
    attempt_id: str
    robot_id: str
    point: InspectionPoint


class InspectionActionContext(Protocol):
    def acquire(
        self,
        *,
        request: AcquisitionRequest,
        received_at_ms: int,
    ) -> MockObservation:
        ...


@dataclass(frozen=True)
class MockReading:
    value: float
    captured_at_ms: int
    complete: bool = True


class DeterministicMockAcquisition:
    """Consumes a fixed sequence of readings; it never reads a real sensor."""

    def __init__(
        self,
        *,
        readings: tuple[MockReading, ...],
        sensor_id: str = 'mock-temperature-sensor',
        calibration_version: str = 'mock-calibration-v1',
    ) -> None:
        if not sensor_id.strip():
            raise ValueError('sensor_id must not be empty.')
        if not calibration_version.strip():
            raise ValueError('calibration_version must not be empty.')
        self._readings = readings
        self._sensor_id = sensor_id
        self._calibration_version = calibration_version
        self._next_index = 0

    def acquire(
        self,
        *,
        request: AcquisitionRequest,
        received_at_ms: int,
    ) -> MockObservation:
        if self._next_index >= len(self._readings):
            raise InspectionAcquisitionError('mock_reading_exhausted')
        reading = self._readings[self._next_index]
        self._next_index += 1
        return MockObservation(
            observation_id=f'{request.attempt_id}:observation',
            item_id=request.point.item.item_id,
            robot_id=request.robot_id,
            point_id=request.point.point_id,
            sensor_id=self._sensor_id,
            frame_id=request.point.frame_id,
            captured_at_ms=reading.captured_at_ms,
            received_at_ms=received_at_ms,
            value=reading.value,
            calibration_version=self._calibration_version,
            complete=reading.complete,
            source='mock',
        )
