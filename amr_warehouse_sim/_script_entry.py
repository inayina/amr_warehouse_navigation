from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Callable

try:
    from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
except ImportError:
    PackageNotFoundError = None
    get_package_share_directory = None


def _package_share_directory() -> Path | None:
    if get_package_share_directory is None:
        return None

    try:
        return Path(get_package_share_directory('amr_warehouse_sim'))
    except Exception as exc:
        if PackageNotFoundError is not None and isinstance(exc, PackageNotFoundError):
            return None
        raise


def _candidate_repo_roots(script_path: Path) -> list[Path]:
    candidates = [
        Path(__file__).resolve().parents[1],
        script_path.resolve().parents[1],
        Path.cwd(),
    ]
    unique_candidates: list[Path] = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def _extend_sys_path_from_local_venv(script_path: Path) -> None:
    for repo_root in _candidate_repo_roots(script_path):
        site_packages_root = repo_root / '.venv' / 'lib'
        if not site_packages_root.is_dir():
            continue

        for version_dir in sorted(site_packages_root.glob('python*/site-packages')):
            resolved_site_packages = str(version_dir.resolve())
            if resolved_site_packages not in sys.path:
                sys.path.insert(0, resolved_site_packages)


def resolve_script_path(script_name: str) -> Path:
    candidates = [
        Path(__file__).resolve().parents[1] / 'scripts' / script_name,
    ]

    package_share = _package_share_directory()

    if package_share is not None:
        candidates.append(package_share / 'scripts' / script_name)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    checked = ', '.join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f'Could not locate {script_name}. Checked: {checked}')


def load_script_module(script_name: str):
    script_path = resolve_script_path(script_name)
    _extend_sys_path_from_local_venv(script_path)
    module_name = f'amr_warehouse_sim_{Path(script_name).stem}_script'
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load module from {script_path}')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_script_main(script_name: str) -> Callable[[list[str] | None], int]:
    module = load_script_module(script_name)
    main = getattr(module, 'main', None)
    if not callable(main):
        raise AttributeError(f'{script_name} does not expose a callable main().')
    return main
