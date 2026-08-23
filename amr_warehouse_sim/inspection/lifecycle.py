from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from .models import (
    EvaluationResult,
    EvidenceReference,
    InspectionRunSnapshot,
    InspectionTask,
    MockObservation,
    ObservationQuality,
    PointAttemptSnapshot,
    QualityResult,
)
from .rules import MaximumThresholdRule, ObservationEvaluator


class InvalidInspectionTransitionError(RuntimeError):
    """Raised when an inspection execution transition is not allowed."""


class InspectionExecutionPhase(str, Enum):
    """Point-local execution state; not a business or Fleet assignment state."""

    IDLE = 'idle'
    NAVIGATING = 'navigating'
    ARRIVED = 'arrived'
    STABILIZING = 'stabilizing'
    ACQUIRING = 'acquiring'
    VALIDATING = 'validating'
    EVALUATING = 'evaluating'
    POINT_SUCCEEDED = 'point_succeeded'
    SUCCEEDED = 'succeeded'
    NAVIGATION_FAILED = 'navigation_failed'
    SENSOR_FAILED = 'sensor_failed'
    DATA_INVALID = 'data_invalid'
    INSPECTION_FAILED = 'inspection_failed'
    CANCELED = 'canceled'


RETRYABLE_PHASES = frozenset(
    {
        InspectionExecutionPhase.NAVIGATION_FAILED,
        InspectionExecutionPhase.SENSOR_FAILED,
        InspectionExecutionPhase.DATA_INVALID,
        InspectionExecutionPhase.INSPECTION_FAILED,
    }
)


@dataclass
class _PointAttempt:
    attempt_id: str
    attempt_number: int
    point_id: str
    phase: InspectionExecutionPhase = InspectionExecutionPhase.IDLE
    navigation_succeeded: bool = False
    arrival_accepted: bool = False
    stabilization_succeeded: bool = False
    observation: MockObservation | None = None
    quality_result: QualityResult | None = None
    evaluation_result: EvaluationResult | None = None
    evidence_reference: EvidenceReference | None = None
    reason: str | None = None

    def snapshot(self) -> PointAttemptSnapshot:
        return PointAttemptSnapshot(
            attempt_id=self.attempt_id,
            attempt_number=self.attempt_number,
            point_id=self.point_id,
            execution_phase=self.phase.value,
            navigation_succeeded=self.navigation_succeeded,
            arrival_accepted=self.arrival_accepted,
            stabilization_succeeded=self.stabilization_succeeded,
            observation=self.observation,
            quality_result=self.quality_result,
            evaluation_result=self.evaluation_result,
            evidence_reference=self.evidence_reference,
            reason=self.reason,
        )


class InspectionRunController:
    """Deterministic one-point P0 inspection lifecycle controller."""

    def __init__(self, *, run_id: str, robot_id: str, task: InspectionTask) -> None:
        if not run_id.strip():
            raise ValueError('run_id must not be empty.')
        if not robot_id.strip():
            raise ValueError('robot_id must not be empty.')
        self._run_id = run_id
        self._robot_id = robot_id
        self._task = task
        self._completed_attempts: list[PointAttemptSnapshot] = []
        self._attempt = self._new_attempt(1)

    @property
    def phase(self) -> InspectionExecutionPhase:
        return self._attempt.phase

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def robot_id(self) -> str:
        return self._robot_id

    @property
    def task(self) -> InspectionTask:
        return self._task

    @property
    def current_attempt_id(self) -> str:
        return self._attempt.attempt_id

    @property
    def snapshot(self) -> InspectionRunSnapshot:
        attempts = (*self._completed_attempts, self._attempt.snapshot())
        return InspectionRunSnapshot(
            run_id=self._run_id,
            task_id=self._task.task_id,
            robot_id=self._robot_id,
            point_id=self._task.point.point_id,
            execution_phase=self.phase.value,
            attempts=attempts,
        )

    def start_navigation(self) -> None:
        self._require_phase(InspectionExecutionPhase.IDLE)
        self._attempt.phase = InspectionExecutionPhase.NAVIGATING

    def record_navigation_result(
        self,
        *,
        succeeded: bool,
        reason: str | None = None,
    ) -> None:
        self._require_phase(InspectionExecutionPhase.NAVIGATING)
        self._attempt.navigation_succeeded = succeeded
        if succeeded:
            self._attempt.phase = InspectionExecutionPhase.ARRIVED
            self._attempt.reason = None
            return
        self._attempt.phase = InspectionExecutionPhase.NAVIGATION_FAILED
        self._attempt.reason = reason or 'navigation_failed'

    def confirm_arrival(
        self,
        *,
        accepted: bool,
        reason: str | None = None,
    ) -> None:
        self._require_phase(InspectionExecutionPhase.ARRIVED)
        self._attempt.arrival_accepted = accepted
        if accepted:
            self._attempt.phase = InspectionExecutionPhase.STABILIZING
            return
        self._attempt.phase = InspectionExecutionPhase.INSPECTION_FAILED
        self._attempt.reason = reason or 'arrival_not_accepted'

    def complete_stabilization(
        self,
        *,
        succeeded: bool,
        reason: str | None = None,
    ) -> None:
        self._require_phase(InspectionExecutionPhase.STABILIZING)
        self._attempt.stabilization_succeeded = succeeded
        if succeeded:
            self._attempt.phase = InspectionExecutionPhase.ACQUIRING
            return
        self._attempt.phase = InspectionExecutionPhase.INSPECTION_FAILED
        self._attempt.reason = reason or 'stabilization_failed'

    def record_observation(self, observation: MockObservation) -> None:
        self._require_phase(InspectionExecutionPhase.ACQUIRING)
        self._attempt.observation = observation
        self._attempt.phase = InspectionExecutionPhase.VALIDATING

    def record_sensor_failure(self, reason: str = 'sensor_failed') -> None:
        self._require_phase(InspectionExecutionPhase.ACQUIRING)
        self._attempt.phase = InspectionExecutionPhase.SENSOR_FAILED
        self._attempt.reason = reason

    def validate_observation(self, *, now_ms: int) -> QualityResult:
        self._require_phase(InspectionExecutionPhase.VALIDATING)
        observation = self._require_observation()
        item = self._task.point.item

        provenance_matches = (
            observation.item_id == item.item_id
            and observation.robot_id == self._robot_id
            and observation.point_id == self._task.point.point_id
            and observation.frame_id == self._task.point.frame_id
        )
        timestamps_valid = (
            observation.captured_at_ms <= observation.received_at_ms <= now_ms
        )

        if not provenance_matches or not isfinite(observation.value):
            result = QualityResult(ObservationQuality.INVALID, 'observation_invalid')
        elif not observation.complete:
            result = QualityResult(ObservationQuality.INCOMPLETE, 'observation_incomplete')
        elif not timestamps_valid:
            result = QualityResult(ObservationQuality.INVALID, 'observation_timestamp_invalid')
        elif now_ms - observation.captured_at_ms > self._task.point.maximum_observation_age_ms:
            result = QualityResult(ObservationQuality.STALE, 'observation_stale')
        else:
            result = QualityResult(ObservationQuality.PASS, 'observation_valid')

        self._attempt.quality_result = result
        if result.passed:
            self._attempt.phase = InspectionExecutionPhase.EVALUATING
        else:
            self._attempt.phase = InspectionExecutionPhase.DATA_INVALID
            self._attempt.reason = result.reason
        return result

    def evaluate(
        self,
        *,
        evaluator: ObservationEvaluator | None = None,
        evaluated_at_ms: int | None = None,
    ) -> EvaluationResult:
        self._require_phase(InspectionExecutionPhase.EVALUATING)
        observation = self._require_observation()
        item = self._task.point.item
        active_evaluator = evaluator or MaximumThresholdRule(
            evaluator_id='p0-maximum-threshold',
            version='1',
            maximum_value=item.maximum_value,
        )
        result = active_evaluator.evaluate(
            observation=observation,
            finding_id=f'{self._attempt.attempt_id}:finding',
            evaluated_at_ms=(
                observation.received_at_ms
                if evaluated_at_ms is None
                else evaluated_at_ms
            ),
        )
        if result.maximum_value != item.maximum_value:
            raise ValueError(
                'Evaluator maximum_value does not match the InspectionItem contract.'
            )
        self._attempt.evaluation_result = result
        return result

    def persist_evidence(self, evidence_reference: EvidenceReference) -> None:
        allowed = {
            InspectionExecutionPhase.NAVIGATION_FAILED,
            InspectionExecutionPhase.EVALUATING,
            InspectionExecutionPhase.DATA_INVALID,
            InspectionExecutionPhase.SENSOR_FAILED,
            InspectionExecutionPhase.INSPECTION_FAILED,
            InspectionExecutionPhase.CANCELED,
        }
        if self.phase not in allowed:
            self._raise_invalid(f'evidence persistence from {self.phase.value}')
        if self._attempt.evidence_reference is not None:
            raise InvalidInspectionTransitionError(
                f'Attempt {self._attempt.attempt_id} already has persisted evidence.'
            )
        self._attempt.evidence_reference = evidence_reference

    def complete_point(self) -> None:
        self._require_phase(InspectionExecutionPhase.EVALUATING)
        missing = []
        if not self._attempt.navigation_succeeded:
            missing.append('navigation')
        if not self._attempt.arrival_accepted:
            missing.append('arrival')
        if not self._attempt.stabilization_succeeded:
            missing.append('stabilization')
        if self._attempt.quality_result is None or not self._attempt.quality_result.passed:
            missing.append('quality')
        if self._attempt.evaluation_result is None:
            missing.append('evaluation')
        if self._attempt.evidence_reference is None:
            missing.append('evidence')
        if missing:
            raise InvalidInspectionTransitionError(
                'Point cannot succeed; missing prerequisites: ' + ', '.join(missing) + '.'
            )
        self._attempt.phase = InspectionExecutionPhase.POINT_SUCCEEDED

    def complete_run(self) -> None:
        self._require_phase(InspectionExecutionPhase.POINT_SUCCEEDED)
        self._attempt.phase = InspectionExecutionPhase.SUCCEEDED

    def retry_point(self) -> None:
        if self.phase not in RETRYABLE_PHASES:
            self._raise_invalid(f'retry from {self.phase.value}')
        self._completed_attempts.append(self._attempt.snapshot())
        self._attempt = self._new_attempt(self._attempt.attempt_number + 1)

    def cancel(self, reason: str = 'canceled') -> None:
        if self.phase in {
            InspectionExecutionPhase.POINT_SUCCEEDED,
            InspectionExecutionPhase.SUCCEEDED,
            InspectionExecutionPhase.CANCELED,
        }:
            self._raise_invalid(f'cancel from {self.phase.value}')
        self._attempt.phase = InspectionExecutionPhase.CANCELED
        self._attempt.reason = reason

    def _new_attempt(self, attempt_number: int) -> _PointAttempt:
        return _PointAttempt(
            attempt_id=(
                f'{self._run_id}:{self._task.point.point_id}:attempt-{attempt_number}'
            ),
            attempt_number=attempt_number,
            point_id=self._task.point.point_id,
        )

    def _require_phase(self, expected: InspectionExecutionPhase) -> None:
        if self.phase is not expected:
            self._raise_invalid(
                f'expected {expected.value}, current phase is {self.phase.value}'
            )

    def _require_observation(self) -> MockObservation:
        if self._attempt.observation is None:
            raise InvalidInspectionTransitionError('Current attempt has no observation.')
        return self._attempt.observation

    def _raise_invalid(self, operation: str) -> None:
        raise InvalidInspectionTransitionError(
            f'Inspection operation is not allowed: {operation}.'
        )
