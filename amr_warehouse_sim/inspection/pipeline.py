from __future__ import annotations

from .acquisition import (
    AcquisitionRequest,
    InspectionAcquisitionError,
    InspectionActionContext,
)
from .evidence import LocalJsonEvidenceStore
from .lifecycle import InspectionExecutionPhase, InspectionRunController
from .report import InspectionReport, build_inspection_report
from .rules import ObservationEvaluator


class InspectionPointProcessor:
    """Runs the post-arrival P0 inspection data path from ACQUIRING onward."""

    def __init__(
        self,
        *,
        acquisition: InspectionActionContext,
        evaluator: ObservationEvaluator,
        evidence_store: LocalJsonEvidenceStore,
    ) -> None:
        self._acquisition = acquisition
        self._evaluator = evaluator
        self._evidence_store = evidence_store

    def process_current_attempt(
        self,
        *,
        controller: InspectionRunController,
        now_ms: int,
    ) -> InspectionReport:
        if controller.phase is not InspectionExecutionPhase.ACQUIRING:
            raise ValueError('InspectionPointProcessor requires ACQUIRING phase.')

        request = AcquisitionRequest(
            run_id=controller.run_id,
            attempt_id=controller.current_attempt_id,
            robot_id=controller.robot_id,
            point=controller.task.point,
        )
        try:
            observation = self._acquisition.acquire(
                request=request,
                received_at_ms=now_ms,
            )
        except InspectionAcquisitionError as error:
            controller.record_sensor_failure(str(error))
            self._persist_current_attempt(controller)
            return self._build_report(controller, now_ms)

        controller.record_observation(observation)
        quality = controller.validate_observation(now_ms=now_ms)
        if not quality.passed:
            self._persist_current_attempt(controller)
            return self._build_report(controller, now_ms)

        controller.evaluate(
            evaluator=self._evaluator,
            evaluated_at_ms=now_ms,
        )
        self._persist_current_attempt(controller)
        controller.complete_point()
        controller.complete_run()
        return self._build_report(controller, now_ms)

    def finalize_current_failure(
        self,
        *,
        controller: InspectionRunController,
        now_ms: int,
    ) -> InspectionReport:
        allowed = {
            InspectionExecutionPhase.NAVIGATION_FAILED,
            InspectionExecutionPhase.SENSOR_FAILED,
            InspectionExecutionPhase.DATA_INVALID,
            InspectionExecutionPhase.INSPECTION_FAILED,
            InspectionExecutionPhase.CANCELED,
        }
        if controller.phase not in allowed:
            raise ValueError('Current inspection attempt is not in a failure phase.')
        if controller.snapshot.current_attempt.evidence_reference is None:
            self._persist_current_attempt(controller)
        return self._build_report(controller, now_ms)

    def _persist_current_attempt(self, controller: InspectionRunController) -> None:
        evidence = self._evidence_store.persist_attempt(
            run_id=controller.run_id,
            attempt=controller.snapshot.current_attempt,
        )
        controller.persist_evidence(evidence)

    @staticmethod
    def _build_report(
        controller: InspectionRunController,
        generated_at_ms: int,
    ) -> InspectionReport:
        return build_inspection_report(
            task=controller.task,
            run=controller.snapshot,
            generated_at_ms=generated_at_ms,
        )
