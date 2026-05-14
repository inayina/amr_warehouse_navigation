#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .mock_wms_db_common import (
    create_task,
    default_db_path,
    default_task_points_path,
    initialize_database,
    list_tasks,
    update_task_status,
)

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8000


def _default_db_path_from_env() -> Path:
    db_path = os.environ.get('MOCK_WMS_DB_PATH')
    return Path(db_path) if db_path else default_db_path()


def _default_task_points_path_from_env() -> Path:
    task_points_path = os.environ.get('MOCK_WMS_TASK_POINTS_PATH')
    return Path(task_points_path) if task_points_path else default_task_points_path()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Run the minimal Mock WMS HTTP API backed by SQLite.'
    )
    parser.add_argument(
        '--host',
        default=os.environ.get('MOCK_WMS_API_HOST', DEFAULT_HOST),
        help=f'HTTP bind host. Defaults to {DEFAULT_HOST}.',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.environ.get('MOCK_WMS_API_PORT', str(DEFAULT_PORT))),
        help=f'HTTP bind port. Defaults to {DEFAULT_PORT}.',
    )
    parser.add_argument(
        '--db',
        '--db-path',
        type=Path,
        default=_default_db_path_from_env(),
        dest='db_path',
        help='SQLite database path. Defaults to data/mock_wms.db under the repo root.',
    )
    parser.add_argument(
        '--task-points',
        type=Path,
        default=_default_task_points_path_from_env(),
        help='Task point YAML path. Defaults to config/task_points.yaml under the repo root.',
    )
    parser.add_argument(
        '--log-level',
        default='info',
        choices=('critical', 'error', 'warning', 'info', 'debug', 'trace'),
        help='uvicorn log level.',
    )
    return parser


def create_app(
    db_path: Path | None = None,
    task_points_path: Path | None = None,
):
    from fastapi import Body, FastAPI, HTTPException, status

    resolved_db_path = Path(db_path or _default_db_path_from_env())
    resolved_task_points_path = Path(task_points_path or _default_task_points_path_from_env())

    app = FastAPI(
        title='Mock WMS HTTP API',
        version='0.1.0',
        description='Minimal REST API for the current SQLite-backed Mock WMS tasks table.',
    )

    def _ensure_database() -> Path:
        return initialize_database(resolved_db_path)

    def _task_or_404(task_id: int) -> dict[str, object]:
        _ensure_database()
        for task in list_tasks(resolved_db_path):
            if int(task['id']) == task_id:
                return task
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Task id={task_id} was not found.',
        )

    @app.get('/health')
    async def health() -> dict[str, str]:
        db_file = _ensure_database()
        return {
            'status': 'ok',
            'db_path': str(db_file),
            'task_points_path': str(resolved_task_points_path),
        }

    @app.post('/tasks', status_code=status.HTTP_201_CREATED)
    async def create_task_endpoint(
        payload: dict[str, object] = Body(...)
    ) -> dict[str, object]:
        raw_target_name = payload.get('target_name')
        if not isinstance(raw_target_name, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='target_name must be a string.',
            )

        target_name = raw_target_name.strip()
        if not target_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='target_name must not be blank.',
            )

        raw_task_name = payload.get('task_name')
        if raw_task_name is not None and not isinstance(raw_task_name, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='task_name must be a string when provided.',
            )

        task_name = raw_task_name.strip() if raw_task_name is not None else None
        if raw_task_name is not None and not task_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='task_name must not be blank.',
            )

        try:
            return create_task(
                requested_target_name=target_name,
                db_path=resolved_db_path,
                task_points_path=resolved_task_points_path,
                task_name=task_name,
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

    @app.get('/tasks')
    async def list_tasks_endpoint() -> dict[str, object]:
        _ensure_database()
        tasks = list_tasks(resolved_db_path)
        return {
            'count': len(tasks),
            'tasks': tasks,
        }

    @app.get('/tasks/{task_id}')
    async def get_task_endpoint(task_id: int) -> dict[str, object]:
        return _task_or_404(task_id)

    @app.patch('/tasks/{task_id}/status')
    async def patch_task_status_endpoint(
        task_id: int,
        payload: dict[str, object] = Body(...)
    ) -> dict[str, object]:
        raw_status = payload.get('status')
        if not isinstance(raw_status, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='status must be a string.',
            )

        task_status = raw_status.strip()
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='status must not be blank.',
            )

        raw_status_reason = payload.get('status_reason')
        if raw_status_reason is not None and not isinstance(raw_status_reason, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='status_reason must be a string when provided.',
            )

        status_reason = None
        if raw_status_reason is not None:
            status_reason = raw_status_reason.strip()
            if not status_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='status_reason must not be blank when provided.',
                )

        try:
            return update_task_status(
                task_id,
                status=task_status,
                db_path=resolved_db_path,
                status_reason=status_reason,
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    return app


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise SystemExit(
            'uvicorn is required to run the Mock WMS HTTP API. '
            'Install the dependencies listed in requirements.txt.'
        ) from exc

    try:
        app = create_app(
            db_path=args.db_path,
            task_points_path=args.task_points,
        )
    except ModuleNotFoundError as exc:
        raise SystemExit(
            'fastapi is required to run the Mock WMS HTTP API. '
            'Install the dependencies listed in requirements.txt.'
        ) from exc

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
