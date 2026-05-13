import ast


REQUIRED_POINT_FIELDS = {
    'frame_id',
    'x',
    'y',
    'yaw',
    'description',
}

REQUIRED_POINT_NAMES = (
    'start_zone',
    'station_a',
    'station_b',
    'shelf_1',
    'shelf_2',
)


def _parse_scalar(value):
    value = value.strip()
    if value == 'TBD':
        return value
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def _parse_task_points_yaml(path):
    points = {}
    current_point = None

    for raw_line in path.read_text(encoding='utf-8').splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        if not raw_line.startswith(' '):
            assert stripped.endswith(':'), f'Invalid top-level YAML line: {raw_line}'
            current_point = stripped[:-1]
            points[current_point] = {}
            continue

        assert current_point is not None, f'Nested field without point header: {raw_line}'
        key, value = stripped.split(':', 1)
        points[current_point][key.strip()] = _parse_scalar(value)

    return points


def test_task_points_yaml_has_expected_structure(repo_root):
    task_points_path = repo_root / 'config' / 'task_points.yaml'
    assert task_points_path.is_file(), 'config/task_points.yaml should exist for V2.2.'

    task_points = _parse_task_points_yaml(task_points_path)
    assert task_points, 'Task point config should not be empty.'

    for point_name in REQUIRED_POINT_NAMES:
        assert point_name in task_points, f'Missing required task point: {point_name}'

    assert any(
        name.startswith('station_') or name.startswith('shelf_')
        for name in task_points
    ), 'Expected at least one station or shelf task point.'

    for point_name, point in task_points.items():
        assert REQUIRED_POINT_FIELDS.issubset(point), (
            f'Task point "{point_name}" is missing required fields.'
        )
        assert point['frame_id'] == 'map', (
            f'Task point "{point_name}" must use frame_id "map".'
        )
        assert isinstance(point['description'], str) and point['description'].strip(), (
            f'Task point "{point_name}" must have a non-empty description.'
        )
        for field_name in ('x', 'y', 'yaw'):
            assert isinstance(point[field_name], (int, float)) or point[field_name] == 'TBD', (
                f'Task point "{point_name}" field "{field_name}" must be numeric or TBD.'
            )
