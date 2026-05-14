# Tests & CI Summary (2026-05-14)

Purpose: concise instructions to run the test-suite locally and recommended CI checks.

Local quick commands

- Run unit + integration tests using the Makefile helper:

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
make test
```

- Alternative with an already prepared Python environment:

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
python3 -m pytest test -q
```

- Colcon-style (within full workspace):

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon test --packages-select amr_warehouse_sim
colcon test-result --verbose
```

Notes and expectations

- The tests exercise: SQLite mock WMS DB, HTTP API contract, executor / runner contract, and Nav2 ready-gate logic (mocked for unit tests).
- Use Python 3.12 with `fastapi`, `uvicorn`, `httpx`, and `pytest` installed (see `requirements.txt`).
- `make test` uses `.venv` when it exists and falls back to the current shell's `python3` otherwise.

CI recommendations

- Run `make test` inside Python 3.12.
- Lightweight CI without ROS can still run the pure-Python tests; ROS-dependent functional smoke tests should skip unless ROS 2 Jazzy packages are available.
- For full integration CI, install system-level ROS deps in the runner image or use a prebuilt container image with Jazzy installed.
- Cache pip installs and the virtualenv between CI runs; run `make test` as the final verification step.
- Optionally run `colcon test` inside an integration job that provisions ROS 2 and Gazebo.

Common troubleshooting

- Missing packages: install via `pip install -r requirements.txt` in the venv.
- ROS-related tests require ROS 2 Jazzy environment sourced; skip / gate heavy integration tests in lightweight CI.
