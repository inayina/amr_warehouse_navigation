from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from .models import EvidenceReference, PointAttemptSnapshot


class EvidenceConflictError(RuntimeError):
    """Raised when an attempt identity is reused with different evidence."""


_SAFE_COMPONENT = re.compile(r'^[A-Za-z0-9_.:-]+$')


def _validate_component(value: str, field_name: str) -> None:
    if not _SAFE_COMPONENT.fullmatch(value):
        raise ValueError(
            f'{field_name} must contain only letters, digits, dot, underscore, colon, or dash.'
        )


class LocalJsonEvidenceStore:
    """P0 local artifact store with immutable, content-hashed JSON records."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        if not self._root.is_dir():
            raise ValueError('Evidence root must be a directory.')

    def persist_attempt(
        self,
        *,
        run_id: str,
        attempt: PointAttemptSnapshot,
    ) -> EvidenceReference:
        _validate_component(run_id, 'run_id')
        _validate_component(attempt.attempt_id, 'attempt_id')
        run_directory = self._root / run_id
        run_directory.mkdir(exist_ok=True)
        artifact_path = run_directory / f'{attempt.attempt_id}.json'
        payload = {
            'schema_version': 'inspection-evidence-v1',
            'run_id': run_id,
            'attempt': asdict(attempt),
        }
        encoded = (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            + '\n'
        ).encode('utf-8')

        try:
            with artifact_path.open('xb') as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if artifact_path.read_bytes() != encoded:
                raise EvidenceConflictError(
                    f'Evidence already exists with different content: {artifact_path}'
                ) from None

        return EvidenceReference(
            uri=artifact_path.as_uri(),
            sha256=sha256(encoded).hexdigest(),
        )
