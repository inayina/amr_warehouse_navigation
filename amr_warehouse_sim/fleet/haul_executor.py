from __future__ import annotations

from datetime import datetime

from .assignment import AssignmentStatus
from .dispatcher import DispatchTask, FleetDispatcher, FleetEvent
from .registry import RobotRegistry
from .robot_state import RobotState
from .simulated_context import SimulatedRobotContext
from .task_lifecycle import (
    HaulExecutionPhase,
    HaulTaskSnapshot,
    InvalidLifecycleTransitionError,
    TERMINAL_EXECUTION_PHASES,
    WmsTaskStatus,
    assert_execution_transition_allowed,
    assert_wms_transition_allowed,
)


class HaulTaskController:
    """Drive a pickup → dropoff haul while keeping three state machines separate."""

    def __init__(
        self,
        *,
        task_id: int,
        pickup_station: str,
        dropoff_station: str,
        dispatcher: FleetDispatcher,
        priority: str = 'normal',
        event_sink: list[FleetEvent] | None = None,
        contexts: dict[str, SimulatedRobotContext] | None = None,
    ):
        if not dropoff_station:
            raise ValueError('Haul tasks require a dropoff_station.')

        self.dispatcher = dispatcher
        self.registry: RobotRegistry = dispatcher.registry
        self._event_sink = event_sink if event_sink is not None else dispatcher._event_sink
        self._contexts = contexts or {}
        self._snapshot = HaulTaskSnapshot(
            task_id=task_id,
            pickup_station=pickup_station,
            dropoff_station=dropoff_station,
            priority=priority,
            wms_status=WmsTaskStatus.PENDING,
            assignment_status=None,
            execution_phase=HaulExecutionPhase.IDLE,
            robot_id=None,
            pickup_completed=False,
            reason=None,
        )
        self._emit(
            'TASK_CREATED',
            reason=f'pickup={pickup_station}; dropoff={dropoff_station}',
        )

    @property
    def snapshot(self) -> HaulTaskSnapshot:
        return self._snapshot

    def _emit(self, event: str, *, reason: str | None = None) -> None:
        fleet_event = self.dispatcher.emit_event(
            event,
            task_id=self._snapshot.task_id,
            robot_id=self._snapshot.robot_id,
            reason=reason,
        )
        if fleet_event not in self._event_sink:
            self._event_sink.append(fleet_event)

    def _context_for(self, robot_id: str) -> SimulatedRobotContext:
        if robot_id not in self._contexts:
            self._contexts[robot_id] = SimulatedRobotContext(robot_id, self.registry)
        return self._contexts[robot_id]

    def _replace_snapshot(self, **changes) -> HaulTaskSnapshot:
        current = self._snapshot
        self._snapshot = HaulTaskSnapshot(
            task_id=changes.get('task_id', current.task_id),
            pickup_station=changes.get('pickup_station', current.pickup_station),
            dropoff_station=changes.get('dropoff_station', current.dropoff_station),
            priority=changes.get('priority', current.priority),
            wms_status=changes.get('wms_status', current.wms_status),
            assignment_status=changes.get('assignment_status', current.assignment_status),
            execution_phase=changes.get('execution_phase', current.execution_phase),
            robot_id=changes.get('robot_id', current.robot_id),
            pickup_completed=changes.get('pickup_completed', current.pickup_completed),
            reason=changes.get('reason', current.reason),
        )
        return self._snapshot

    def _set_wms_status(self, target: WmsTaskStatus, *, reason: str | None = None) -> None:
        assert_wms_transition_allowed(self._snapshot.wms_status, target)
        self._replace_snapshot(wms_status=target, reason=reason)

    def _set_execution_phase(
        self,
        target: HaulExecutionPhase,
        *,
        reason: str | None = None,
        pickup_completed: bool | None = None,
    ) -> None:
        assert_execution_transition_allowed(self._snapshot.execution_phase, target)
        changes = {'execution_phase': target, 'reason': reason}
        if pickup_completed is not None:
            changes['pickup_completed'] = pickup_completed
        self._replace_snapshot(**changes)

    def _sync_assignment_status(self, status: AssignmentStatus) -> None:
        if self.dispatcher.get_assignment_record(self._snapshot.task_id) is None:
            self._replace_snapshot(assignment_status=status)
            return
        updated = self.dispatcher.set_assignment_status(self._snapshot.task_id, status)
        self._replace_snapshot(assignment_status=updated.status)

    def _release_robot(self) -> None:
        robot_id = self._snapshot.robot_id
        if robot_id is None:
            return
        robot = self.registry.get_robot(robot_id)
        if robot.state in {RobotState.ASSIGNED, RobotState.BUSY}:
            self.registry.release_task(robot_id)

    def assign(self, *, now: datetime, heartbeat_timeout_sec: float = 30.0) -> HaulTaskSnapshot:
        previous_wms = self._snapshot.wms_status
        if previous_wms not in {WmsTaskStatus.PENDING, WmsTaskStatus.REQUEUED}:
            raise InvalidLifecycleTransitionError(
                'Only PENDING or REQUEUED haul tasks can be assigned.'
            )

        if previous_wms == WmsTaskStatus.REQUEUED:
            self._set_execution_phase(
                HaulExecutionPhase.IDLE,
                pickup_completed=False,
                reason='Reset execution after requeue.',
            )

        assignment = self.dispatcher.assign_task(
            DispatchTask(
                task_id=self._snapshot.task_id,
                pickup_station=self._snapshot.pickup_station,
                dropoff_station=self._snapshot.dropoff_station,
                priority=self._snapshot.priority,
            ),
            now=now,
            heartbeat_timeout_sec=heartbeat_timeout_sec,
        )
        self._replace_snapshot(
            robot_id=assignment.robot_id,
            assignment_status=assignment.status,
        )
        self._set_wms_status(WmsTaskStatus.ASSIGNED, reason=assignment.dispatch_reason)
        if previous_wms == WmsTaskStatus.REQUEUED:
            self._emit(
                'TASK_REASSIGNED',
                reason=f'reassigned to {assignment.robot_id}',
            )
        return self._snapshot

    def start(self) -> HaulTaskSnapshot:
        if self._snapshot.robot_id is None:
            raise InvalidLifecycleTransitionError('Cannot start a haul task before assignment.')

        self._set_wms_status(
            WmsTaskStatus.IN_PROGRESS,
            reason='Haul execution started.',
        )
        self._sync_assignment_status(AssignmentStatus.EXECUTING)
        self._set_execution_phase(
            HaulExecutionPhase.NAVIGATING_TO_PICKUP,
            reason=f'Navigate to pickup {self._snapshot.pickup_station}.',
        )
        self._emit(
            'NAV_STARTED',
            reason=f'target={self._snapshot.pickup_station}',
        )
        robot = self.registry.get_robot(self._snapshot.robot_id)
        if robot.state == RobotState.ASSIGNED:
            self.registry.mark_busy(self._snapshot.robot_id)
            self._emit('ROBOT_BUSY', reason='Haul navigation started.')
        return self._snapshot

    def _navigate(self, *, simulate_failure: bool = False):
        if self._snapshot.robot_id is None:
            raise InvalidLifecycleTransitionError('Haul task has no assigned robot.')
        return self._context_for(self._snapshot.robot_id).navigate_to_pose(
            simulate_failure=simulate_failure,
        )

    def complete_navigation_to_pickup(
        self,
        *,
        simulate_failure: bool = False,
    ) -> HaulTaskSnapshot:
        if self._snapshot.execution_phase != HaulExecutionPhase.NAVIGATING_TO_PICKUP:
            raise InvalidLifecycleTransitionError(
                'Navigation to pickup can only complete from NAVIGATING_TO_PICKUP.'
            )

        result = self._navigate(simulate_failure=simulate_failure)
        if not result.succeeded:
            return self.fail(result.reason)

        self.registry.set_current_station(
            self._snapshot.robot_id,
            self._snapshot.pickup_station,
        )
        self._set_execution_phase(
            HaulExecutionPhase.PICKUP,
            reason='Arrived at pickup; simulating acknowledgement.',
        )
        self._emit('NAV_SUCCEEDED', reason=f'arrived={self._snapshot.pickup_station}')
        return self._snapshot

    def complete_pickup(self) -> HaulTaskSnapshot:
        if self._snapshot.execution_phase != HaulExecutionPhase.PICKUP:
            raise InvalidLifecycleTransitionError(
                'Pickup acknowledgement can only complete from PICKUP.'
            )

        self._set_execution_phase(
            HaulExecutionPhase.NAVIGATING_TO_DROPOFF,
            pickup_completed=True,
            reason='Pickup acknowledged; navigating to dropoff.',
        )
        self._emit(
            'NAV_STARTED',
            reason=f'target={self._snapshot.dropoff_station}',
        )
        return self._snapshot

    def complete_navigation_to_dropoff(
        self,
        *,
        simulate_failure: bool = False,
    ) -> HaulTaskSnapshot:
        if self._snapshot.execution_phase != HaulExecutionPhase.NAVIGATING_TO_DROPOFF:
            raise InvalidLifecycleTransitionError(
                'Navigation to dropoff can only complete from NAVIGATING_TO_DROPOFF.'
            )

        result = self._navigate(simulate_failure=simulate_failure)
        if not result.succeeded:
            return self.fail(result.reason)

        self.registry.set_current_station(
            self._snapshot.robot_id,
            self._snapshot.dropoff_station,
        )
        self._set_execution_phase(
            HaulExecutionPhase.DROPOFF,
            reason='Arrived at dropoff; simulating acknowledgement.',
        )
        self._emit('NAV_SUCCEEDED', reason=f'arrived={self._snapshot.dropoff_station}')
        return self._snapshot

    def complete_dropoff(self) -> HaulTaskSnapshot:
        if self._snapshot.execution_phase != HaulExecutionPhase.DROPOFF:
            raise InvalidLifecycleTransitionError(
                'Dropoff acknowledgement can only complete from DROPOFF.'
            )

        self._set_execution_phase(
            HaulExecutionPhase.SUCCEEDED,
            reason='Dropoff acknowledged.',
        )
        self._set_wms_status(WmsTaskStatus.SUCCEEDED, reason='Haul task succeeded.')
        self._sync_assignment_status(AssignmentStatus.COMPLETED)
        self._release_robot()
        self._emit('TASK_SUCCEEDED', reason='pickup/dropoff haul completed.')
        return self._snapshot

    def fail(self, reason: str) -> HaulTaskSnapshot:
        if self._snapshot.execution_phase not in TERMINAL_EXECUTION_PHASES:
            self._set_execution_phase(HaulExecutionPhase.FAILED, reason=reason)
        if self._snapshot.wms_status not in {
            WmsTaskStatus.SUCCEEDED,
            WmsTaskStatus.FAILED,
            WmsTaskStatus.CANCELED,
        }:
            if self._snapshot.wms_status == WmsTaskStatus.PENDING:
                raise InvalidLifecycleTransitionError(
                    'A PENDING haul task cannot fail before assignment.'
                )
            self._set_wms_status(WmsTaskStatus.FAILED, reason=reason)
        if self._snapshot.assignment_status in {
            AssignmentStatus.ASSIGNED,
            AssignmentStatus.EXECUTING,
        }:
            self._sync_assignment_status(AssignmentStatus.FAILED)
        self._release_robot()
        return self._snapshot

    def cancel(self, reason: str = 'Task canceled.') -> HaulTaskSnapshot:
        if self._snapshot.pickup_completed:
            raise InvalidLifecycleTransitionError(
                'Cancel after completed pickup is not modeled in Stage 3; '
                'treat as FAILED instead.'
            )
        self._set_execution_phase(HaulExecutionPhase.CANCELED, reason=reason)
        self._set_wms_status(WmsTaskStatus.CANCELED, reason=reason)
        if self._snapshot.assignment_status in {
            AssignmentStatus.ASSIGNED,
            AssignmentStatus.EXECUTING,
        }:
            self._sync_assignment_status(AssignmentStatus.CANCELED)
        self._release_robot()
        return self._snapshot

    def requeue(self, reason: str = 'Task requeued.') -> HaulTaskSnapshot:
        if self._snapshot.pickup_completed:
            raise InvalidLifecycleTransitionError(
                'Cannot requeue after pickup is complete; load is considered irreversible.'
            )
        self._set_execution_phase(HaulExecutionPhase.REQUEUED, reason=reason)
        self._set_wms_status(WmsTaskStatus.REQUEUED, reason=reason)
        if self._snapshot.assignment_status in {
            AssignmentStatus.ASSIGNED,
            AssignmentStatus.EXECUTING,
        }:
            self._sync_assignment_status(AssignmentStatus.RELEASED)
        self._release_robot()
        self._replace_snapshot(robot_id=None)
        self._emit('TASK_REQUEUED', reason=reason)
        return self._snapshot

    def run_simulated_success(self, *, now: datetime) -> HaulTaskSnapshot:
        self.assign(now=now)
        self.start()
        self.complete_navigation_to_pickup()
        self.complete_pickup()
        self.complete_navigation_to_dropoff()
        return self.complete_dropoff()
