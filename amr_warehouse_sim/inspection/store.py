from __future__ import annotations

import json
from pathlib import Path
import sqlite3


_SCHEMA = """
CREATE TABLE IF NOT EXISTS inspection_runs (
    run_id TEXT PRIMARY KEY,
    robot_id TEXT NOT NULL,
    route_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    result_summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inspection_point_results (
    run_id TEXT NOT NULL,
    point_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    status TEXT NOT NULL,
    navigation_result TEXT NOT NULL,
    captured_at INTEGER,
    evaluation TEXT,
    severity TEXT,
    reason TEXT NOT NULL,
    artifact_ref TEXT,
    result_ref TEXT,
    PRIMARY KEY (run_id, point_id),
    FOREIGN KEY (run_id) REFERENCES inspection_runs(run_id)
);
"""


class InspectionStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    def start_run(
        self,
        *,
        run_id: str,
        robot_id: str,
        route_id: str,
        started_at: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO inspection_runs(
                    run_id, robot_id, route_id, status, started_at, result_summary
                ) VALUES (?, ?, ?, 'running', ?, '{}')
                """,
                (run_id, robot_id, route_id, started_at),
            )

    def persist_point_result(self, result: dict[str, object]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO inspection_point_results(
                    run_id, point_id, sequence, status, navigation_result,
                    captured_at, evaluation, severity, reason, artifact_ref, result_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result['run_id'],
                    result['point_id'],
                    result['sequence'],
                    result['status'],
                    json.dumps(result['navigation_result'], sort_keys=True),
                    result.get('captured_at_ns'),
                    result.get('evaluation'),
                    result.get('severity'),
                    result['reason'],
                    result.get('artifact_ref'),
                    result.get('result_ref'),
                ),
            )

    def finish_run(
        self,
        *,
        run_id: str,
        status: str,
        finished_at: str,
        summary: dict[str, object],
    ) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE inspection_runs
                SET status = ?, finished_at = ?, result_summary = ?
                WHERE run_id = ?
                """,
                (status, finished_at, json.dumps(summary, sort_keys=True), run_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f'Unknown inspection run: {run_id}')

    def get_run(self, run_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                'SELECT * FROM inspection_runs WHERE run_id = ?', (run_id,)
            ).fetchone()
        return None if row is None else dict(row)

    def list_point_results(self, run_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT * FROM inspection_point_results
                WHERE run_id = ? ORDER BY sequence
                """,
                (run_id,),
            ).fetchall()
        return [dict(row) for row in rows]
