from __future__ import annotations

import importlib.util
from pathlib import Path

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


def resolve_extension_root():
    candidates = [Path(__file__).resolve().parents[1] / 'future_extensions' / 'wms_integration']

    try:
        package_share = Path(get_package_share_directory('amr_warehouse_sim'))
        candidates.append(package_share / 'future_extensions' / 'wms_integration')
    except PackageNotFoundError:
        pass

    for candidate in candidates:
        if (candidate / 'task_manager' / 'wms_dispatcher.py').is_file():
            return candidate

    raise FileNotFoundError(
        'Could not locate future_extensions/wms_integration assets for mock WMS.'
    )


def load_dispatcher_main(extension_root: Path):
    module_path = extension_root / 'task_manager' / 'wms_dispatcher.py'
    spec = importlib.util.spec_from_file_location('mock_wms_dispatcher', module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load dispatcher module from {module_path}')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    dispatcher_main = getattr(module, 'main', None)
    if not callable(dispatcher_main):
        raise AttributeError(f'Module {module_path} does not expose a callable main()')

    return dispatcher_main


def main():
    extension_root = resolve_extension_root()
    dispatcher_main = load_dispatcher_main(extension_root)
    dispatcher_main()


if __name__ == '__main__':
    main()
