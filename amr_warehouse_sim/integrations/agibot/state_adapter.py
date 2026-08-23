from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ...fleet.registry import (
    RobotRecord,
    RobotRegistry,
    default_fleet_db_path,
    repo_root,
)

DEFAULT_ROBOT_ID = 'robot_02'
EXPECTED_EVENT = 'telemetry'
EXPECTED_VENDOR = 'agibot'
EXPECTED_MODEL = 'd1_maxpro'
DEFAULT_INTERVAL_MS = 1000
PROBE_SHUTDOWN_TIMEOUT_SEC = 5.0


class AgibotDependencyError(RuntimeError):
    """Raised when the optional vendor-side probe is unavailable."""


class AgibotProbeProcessError(RuntimeError):
    """Raised when the vendor-side probe exits without a clean contract result."""


class AgibotIpcEventError(ValueError):
    """Raised when one probe stdout line violates the experimental JSONL contract."""


@dataclass(frozen=True)
class ProbeRunResult:
    returncode: int
    telemetry_events: int
    rejected_events: int
    interrupted: bool = False


class AgibotStateAdapter:
    """Map normalized Agibot probe events to Fleet transport liveness.

    The C++ SDK lifecycle and vendor network protocol stay outside this class.
    A valid normalized event proves only that the probe completed one read-only
    telemetry call; it does not establish a Fleet business or execution state.
    """

    def __init__(self, *, registry: RobotRegistry, robot_id: str = DEFAULT_ROBOT_ID):
        registry.get_robot(robot_id)
        self.registry = registry
        self.robot_id = robot_id
        self.receive_count = 0
        self.rejected_count = 0

    def on_vendor_telemetry_received(self, *, timestamp: str | None = None) -> RobotRecord:
        self.receive_count += 1
        return self.registry.record_heartbeat(
            self.robot_id,
            timestamp=timestamp,
            recover_offline=False,
        )

    def on_probe_line(
        self,
        line: str,
        *,
        timestamp: str | None = None,
    ) -> RobotRecord | None:
        try:
            parse_probe_event(line)
        except AgibotIpcEventError:
            self.rejected_count += 1
            return None
        return self.on_vendor_telemetry_received(timestamp=timestamp)


def parse_probe_event(line: str) -> dict[str, object]:
    try:
        payload = json.loads(line)
    except (json.JSONDecodeError, TypeError) as exc:
        raise AgibotIpcEventError('Probe output is not valid JSON.') from exc

    if not isinstance(payload, dict):
        raise AgibotIpcEventError('Probe event must be a JSON object.')

    expected = {
        'event': EXPECTED_EVENT,
        'vendor': EXPECTED_VENDOR,
        'model': EXPECTED_MODEL,
    }
    for field, expected_value in expected.items():
        if payload.get(field) != expected_value:
            raise AgibotIpcEventError(
                f'Probe event field {field!r} must equal {expected_value!r}.'
            )
    return payload


def default_probe_path() -> Path:
    return (
        repo_root()
        / 'vendor_audit'
        / 'agibot-probe-build'
        / 'agibot_d1_maxpro_state_probe'
    )


def validate_probe_executable(probe_executable: Path) -> Path:
    probe_path = Path(probe_executable)
    if not probe_path.is_file() or not os.access(probe_path, os.X_OK):
        raise AgibotDependencyError(
            'Agibot integration requires the optional D1 MaxPro C++ state probe. '
            'Build the vendor-side probe against the official Agibot D1 MaxPro SDK first. '
            f'Expected executable: {probe_path}'
        )
    return probe_path


def run_probe_process(
    *,
    adapter: AgibotStateAdapter,
    probe_executable: Path,
    probe_args: Sequence[str] = (),
    shutdown_timeout_sec: float = PROBE_SHUTDOWN_TIMEOUT_SEC,
) -> ProbeRunResult:
    probe_path = validate_probe_executable(probe_executable)
    command = [str(probe_path), *probe_args]
    initial_receive_count = adapter.receive_count
    initial_rejected_count = adapter.rejected_count

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        raise AgibotDependencyError(
            f'Failed to start Agibot D1 MaxPro state probe {probe_path}: {exc}'
        ) from exc

    interrupted = False
    try:
        if process.stdout is None:
            raise AgibotProbeProcessError('Agibot probe stdout pipe was not created.')
        for line in process.stdout:
            adapter.on_probe_line(line)
        returncode = process.wait()
    except KeyboardInterrupt:
        interrupted = True
        process.send_signal(signal.SIGINT)
        try:
            returncode = process.wait(timeout=max(shutdown_timeout_sec, 0.0))
        except subprocess.TimeoutExpired:
            process.terminate()
            returncode = process.wait(timeout=max(shutdown_timeout_sec, 0.0))
    finally:
        if process.stdout is not None:
            process.stdout.close()

    telemetry_events = adapter.receive_count - initial_receive_count
    rejected_events = adapter.rejected_count - initial_rejected_count
    result = ProbeRunResult(
        returncode=returncode,
        telemetry_events=telemetry_events,
        rejected_events=rejected_events,
        interrupted=interrupted,
    )
    if interrupted:
        return result
    if returncode != 0:
        raise AgibotProbeProcessError(
            f'Agibot state probe exited with code {returncode}; '
            f'valid telemetry events={telemetry_events}, '
            f'rejected lines={rejected_events}.'
        )
    if telemetry_events == 0:
        raise AgibotProbeProcessError(
            'Agibot state probe reached EOF before any valid telemetry event; '
            f'rejected lines={rejected_events}.'
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Opt-in Agibot D1 MaxPro C++ probe JSONL adapter. '
            'Updates Fleet Registry heartbeat only.'
        )
    )
    parser.add_argument('--robot-id', default=DEFAULT_ROBOT_ID)
    parser.add_argument('--fleet-db', type=Path, default=default_fleet_db_path())
    parser.add_argument('--probe', type=Path, default=default_probe_path())
    parser.add_argument('--interval-ms', type=int, default=DEFAULT_INTERVAL_MS)
    parser.add_argument('--once', action='store_true')
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.interval_ms <= 0:
        raise SystemExit('--interval-ms must be greater than zero.')

    registry = RobotRegistry(db_path=args.fleet_db, auto_seed=True)
    adapter = AgibotStateAdapter(registry=registry, robot_id=args.robot_id)
    probe_args = ['--interval-ms', str(args.interval_ms)]
    if args.once:
        probe_args.append('--once')

    try:
        result = run_probe_process(
            adapter=adapter,
            probe_executable=args.probe,
            probe_args=probe_args,
        )
    except (AgibotDependencyError, AgibotProbeProcessError) as exc:
        raise SystemExit(str(exc)) from exc

    print(
        f'Agibot adapter received {result.telemetry_events} valid event(s); '
        f'rejected {result.rejected_events} line(s); '
        f'probe exit code={result.returncode}.'
    )


if __name__ == '__main__':
    main()
