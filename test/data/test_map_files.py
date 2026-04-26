import ast


def _parse_simple_yaml(path):
    data = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        key, value = line.split(':', 1)
        data[key.strip()] = value.strip()
    return data


def test_nav2_map_entry_points_to_existing_pgm(repo_root):
    map_yaml = repo_root / 'maps' / 'warehouse.yaml'
    assert map_yaml.is_file(), 'maps/warehouse.yaml should exist as the Nav2 map entry.'

    metadata = _parse_simple_yaml(map_yaml)
    image_name = metadata['image']
    image_path = map_yaml.parent / image_name

    assert image_name.endswith('.pgm')
    assert image_path.is_file(), f'Map image does not exist: {image_path}'


def test_nav2_map_entry_has_required_metadata(repo_root):
    map_yaml = repo_root / 'maps' / 'warehouse.yaml'
    metadata = _parse_simple_yaml(map_yaml)

    for required_key in (
        'image',
        'mode',
        'resolution',
        'origin',
        'negate',
        'occupied_thresh',
        'free_thresh',
    ):
        assert required_key in metadata, f'Missing map key: {required_key}'

    assert metadata['mode'] == 'trinary'
    assert float(metadata['resolution']) > 0.0
    assert int(metadata['negate']) in (0, 1)
    assert 0.0 < float(metadata['free_thresh']) < 1.0
    assert 0.0 < float(metadata['occupied_thresh']) < 1.0

    origin = ast.literal_eval(metadata['origin'])
    assert len(origin) == 3
