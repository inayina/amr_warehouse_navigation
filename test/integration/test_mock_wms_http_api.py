import importlib.util

import pytest


def _load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def httpx_module():
    return pytest.importorskip('httpx')


@pytest.fixture
def mock_wms_api_app(tmp_path, repo_root):
    pytest.importorskip('fastapi')
    db_path = tmp_path / 'mock_wms_http_api.db'
    task_points_path = repo_root / 'config' / 'task_points.yaml'
    module = _load_module(repo_root / 'scripts' / 'mock_wms_api.py', 'mock_wms_api')
    app = module.create_app(
        db_path=db_path,
        task_points_path=task_points_path,
    )
    return {
        'app': app,
        'db_path': db_path,
    }


@pytest.mark.anyio
async def test_health_initializes_database_and_returns_paths(mock_wms_api_app, httpx_module):
    async with httpx_module.AsyncClient(
        transport=httpx_module.ASGITransport(app=mock_wms_api_app['app']),
        base_url='http://testserver',
    ) as client:
        response = await client.get('/health')
        payload = response.json()

    assert response.status_code == 200
    assert payload['status'] == 'ok'
    assert payload['db_path'] == str(mock_wms_api_app['db_path'])
    assert mock_wms_api_app['db_path'].is_file()


@pytest.mark.anyio
async def test_post_and_get_task_round_trip(mock_wms_api_app, httpx_module):
    async with httpx_module.AsyncClient(
        transport=httpx_module.ASGITransport(app=mock_wms_api_app['app']),
        base_url='http://testserver',
    ) as client:
        response = await client.post(
            '/tasks',
            json={
                'target_name': 'station_a',
                'task_name': 'http-api-station-a',
            },
        )
        created_task = response.json()

        assert response.status_code == 201
        assert created_task['id'] == 1
        assert created_task['task_name'] == 'http-api-station-a'
        assert created_task['target_name'] == 'station_a'
        assert created_task['status'] == 'pending'

        list_response = await client.get('/tasks')
        list_payload = list_response.json()
        assert list_response.status_code == 200
        assert list_payload['count'] == 1
        assert list_payload['tasks'][0]['id'] == created_task['id']

        get_response = await client.get(f'/tasks/{created_task["id"]}')
        fetched_task = get_response.json()
        assert get_response.status_code == 200
        assert fetched_task == created_task


@pytest.mark.anyio
async def test_patch_task_status_round_trip(mock_wms_api_app, httpx_module):
    async with httpx_module.AsyncClient(
        transport=httpx_module.ASGITransport(app=mock_wms_api_app['app']),
        base_url='http://testserver',
    ) as client:
        create_response = await client.post(
            '/tasks',
            json={
                'target_name': 'station_a',
                'task_name': 'http-api-status-update',
            },
        )
        created_task = create_response.json()

        patch_response = await client.patch(
            f'/tasks/{created_task["id"]}/status',
            json={
                'status': 'running',
                'status_reason': 'Executor claimed the task.',
            },
        )
        patched_task = patch_response.json()

        assert patch_response.status_code == 200
        assert patched_task['id'] == created_task['id']
        assert patched_task['status'] == 'running'
        assert patched_task['status_reason'] == 'Executor claimed the task.'

        get_response = await client.get(f'/tasks/{created_task["id"]}')
        fetched_task = get_response.json()
        assert get_response.status_code == 200
        assert fetched_task['status'] == 'running'
        assert fetched_task['status_reason'] == 'Executor claimed the task.'


@pytest.mark.anyio
async def test_get_task_returns_404_for_unknown_id(mock_wms_api_app, httpx_module):
    async with httpx_module.AsyncClient(
        transport=httpx_module.ASGITransport(app=mock_wms_api_app['app']),
        base_url='http://testserver',
    ) as client:
        response = await client.get('/tasks/999')
        error_payload = response.json()

        assert response.status_code == 404
        assert error_payload == {'detail': 'Task id=999 was not found.'}


@pytest.mark.anyio
async def test_patch_task_status_returns_404_for_unknown_id(mock_wms_api_app, httpx_module):
    async with httpx_module.AsyncClient(
        transport=httpx_module.ASGITransport(app=mock_wms_api_app['app']),
        base_url='http://testserver',
    ) as client:
        response = await client.patch(
            '/tasks/999/status',
            json={
                'status': 'running',
            },
        )
        error_payload = response.json()

        assert response.status_code == 404
        assert error_payload == {'detail': "'Task id=999 was not found.'"}


@pytest.mark.anyio
async def test_invalid_target_is_rejected(mock_wms_api_app, httpx_module):
    async with httpx_module.AsyncClient(
        transport=httpx_module.ASGITransport(app=mock_wms_api_app['app']),
        base_url='http://testserver',
    ) as client:
        response = await client.post(
            '/tasks',
            json={
                'target_name': 'start_zone',
            },
        )

        error_payload = response.json()
        assert response.status_code == 400
        assert 'validated task targets' in error_payload['detail']


@pytest.mark.anyio
async def test_patch_task_status_rejects_invalid_status(mock_wms_api_app, httpx_module):
    async with httpx_module.AsyncClient(
        transport=httpx_module.ASGITransport(app=mock_wms_api_app['app']),
        base_url='http://testserver',
    ) as client:
        create_response = await client.post(
            '/tasks',
            json={
                'target_name': 'station_a',
            },
        )
        created_task = create_response.json()

        response = await client.patch(
            f'/tasks/{created_task["id"]}/status',
            json={
                'status': 'queued',
            },
        )

        error_payload = response.json()
        assert response.status_code == 400
        assert 'Unsupported task status' in error_payload['detail']
