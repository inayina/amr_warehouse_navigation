from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from .models import (
    EvaluationResult,
    FindingOutcome,
    FindingSeverity,
    InspectionFinding,
    MockObservation,
)


class ObservationEvaluator(Protocol):
    maximum_value: float

    def evaluate(
        self,
        *,
        observation: MockObservation,
        finding_id: str,
        evaluated_at_ms: int,
    ) -> EvaluationResult:
        ...


@dataclass(frozen=True)
class MaximumThresholdRule:
    """Deterministic local rule used by the P0 mock inspection slice."""

    evaluator_id: str
    version: str
    maximum_value: float

    def __post_init__(self) -> None:
        if not self.evaluator_id.strip():
            raise ValueError('evaluator_id must not be empty.')
        if not self.version.strip():
            raise ValueError('version must not be empty.')
        if not isfinite(self.maximum_value):
            raise ValueError('maximum_value must be finite.')

    def evaluate(
        self,
        *,
        observation: MockObservation,
        finding_id: str,
        evaluated_at_ms: int,
    ) -> EvaluationResult:
        anomalous = observation.value > self.maximum_value
        finding = InspectionFinding(
            finding_id=finding_id,
            outcome=(
                FindingOutcome.ANOMALOUS if anomalous else FindingOutcome.NORMAL
            ),
            severity=FindingSeverity.WARNING if anomalous else None,
            reason='value_above_maximum' if anomalous else 'value_within_maximum',
        )
        return EvaluationResult(
            observation_id=observation.observation_id,
            measured_value=observation.value,
            maximum_value=self.maximum_value,
            evaluator_id=self.evaluator_id,
            evaluator_version=self.version,
            evaluated_at_ms=evaluated_at_ms,
            finding=finding,
        )
