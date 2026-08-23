from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json

from .models import InspectionRunSnapshot, InspectionTask, PointAttemptSnapshot


class ReportCompletion(str, Enum):
    IN_PROGRESS = 'in_progress'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELED = 'canceled'


_FAILED_PHASES = frozenset(
    {
        'navigation_failed',
        'sensor_failed',
        'data_invalid',
        'inspection_failed',
    }
)


@dataclass(frozen=True)
class AttemptReport:
    attempt_id: str
    attempt_number: int
    execution_phase: str
    observation: dict[str, object] | None
    quality: dict[str, object] | None
    evaluation: dict[str, object] | None
    finding: dict[str, object] | None
    evidence: dict[str, object] | None
    system_fault: dict[str, str] | None


@dataclass(frozen=True)
class InspectionReport:
    report_id: str
    generated_at_ms: int
    run_id: str
    task_id: str
    robot_id: str
    point: dict[str, object]
    completion: ReportCompletion
    retry_count: int
    attempts: tuple[AttemptReport, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['completion'] = self.completion.value
        return payload

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


def _attempt_report(attempt: PointAttemptSnapshot) -> AttemptReport:
    evaluation = (
        None if attempt.evaluation_result is None else asdict(attempt.evaluation_result)
    )
    finding = (
        None
        if attempt.evaluation_result is None
        else asdict(attempt.evaluation_result.finding)
    )
    system_fault = None
    if attempt.execution_phase in _FAILED_PHASES:
        system_fault = {
            'code': attempt.execution_phase,
            'reason': attempt.reason or attempt.execution_phase,
        }
    return AttemptReport(
        attempt_id=attempt.attempt_id,
        attempt_number=attempt.attempt_number,
        execution_phase=attempt.execution_phase,
        observation=(
            None if attempt.observation is None else asdict(attempt.observation)
        ),
        quality=(
            None if attempt.quality_result is None else asdict(attempt.quality_result)
        ),
        evaluation=evaluation,
        finding=finding,
        evidence=(
            None if attempt.evidence_reference is None else asdict(attempt.evidence_reference)
        ),
        system_fault=system_fault,
    )


def build_inspection_report(
    *,
    task: InspectionTask,
    run: InspectionRunSnapshot,
    generated_at_ms: int,
) -> InspectionReport:
    if run.task_id != task.task_id or run.point_id != task.point.point_id:
        raise ValueError('Run snapshot does not match the InspectionTask contract.')

    if run.execution_phase == 'succeeded':
        completion = ReportCompletion.SUCCEEDED
    elif run.execution_phase == 'canceled':
        completion = ReportCompletion.CANCELED
    elif run.execution_phase in _FAILED_PHASES:
        completion = ReportCompletion.FAILED
    else:
        completion = ReportCompletion.IN_PROGRESS

    point = task.point
    return InspectionReport(
        report_id=f'{run.run_id}:report',
        generated_at_ms=generated_at_ms,
        run_id=run.run_id,
        task_id=run.task_id,
        robot_id=run.robot_id,
        point={
            'point_id': point.point_id,
            'frame_id': point.frame_id,
            'x': point.x,
            'y': point.y,
            'yaw': point.yaw,
            'item_id': point.item.item_id,
            'item_kind': point.item.kind,
            'maximum_value': point.item.maximum_value,
        },
        completion=completion,
        retry_count=max(0, len(run.attempts) - 1),
        attempts=tuple(_attempt_report(attempt) for attempt in run.attempts),
    )
