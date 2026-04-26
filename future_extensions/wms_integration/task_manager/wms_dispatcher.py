from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path


GOAL_STATUS_LABELS = {
    0: 'unknown',
    1: 'accepted',
    2: 'executing',
    3: 'canceling',
    4: 'succeeded',
    5: 'canceled',
    6: 'aborted',
}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def normalize_waypoints(path: Path):
    raw = load_json(path)
    frame_id = raw.get('frame_id', 'map')
    waypoints = raw.get('waypoints')

    if not isinstance(waypoints, dict) or not waypoints:
        raise ValueError('Waypoints file must contain a non-empty "waypoints" object.')

    normalized = {}
    for name, pose in waypoints.items():
        if not isinstance(pose, dict):
            raise ValueError(f'Waypoint "{name}" must be an object.')

        for required_key in ('x', 'y', 'yaw'):
            if required_key not in pose:
                raise ValueError(f'Waypoint "{name}" is missing "{required_key}".')

        normalized[name] = {
            'x': float(pose['x']),
            'y': float(pose['y']),
            'yaw': float(pose['yaw']),
            'description': str(pose.get('description', '')),
        }

    return {
        'frame_id': frame_id,
        'waypoints': normalized,
    }


def normalize_task_queue(path: Path, waypoint_names):
    raw = load_json(path)
    tasks = raw.get('tasks')

    if not isinstance(tasks, list) or not tasks:
        raise ValueError('Task queue file must contain a non-empty "tasks" array.')

    normalized_tasks = []
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError('Each task must be an object.')

        task_id = str(task.get('task_id', '')).strip()
        if not task_id:
            raise ValueError('Each task must define a non-empty "task_id".')

        steps = task.get('steps')
        if not isinstance(steps, list) or not steps:
            raise ValueError(f'Task "{task_id}" must define a non-empty "steps" array.')

        normalized_steps = []
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                raise ValueError(f'Task "{task_id}" step {index} must be an object.')

            waypoint_name = str(step.get('waypoint', '')).strip()
            if waypoint_name not in waypoint_names:
                raise ValueError(
                    f'Task "{task_id}" step {index} references unknown waypoint "{waypoint_name}".'
                )

            normalized_steps.append(
                {
                    'step_id': f'{task_id}-S{index:02d}',
                    'waypoint': waypoint_name,
                    'action': str(step.get('action', 'navigate')),
                    'pause_sec': float(step.get('pause_sec', 0.0)),
                }
            )

        normalized_tasks.append(
            {
                'task_id': task_id,
                'type': str(task.get('type', 'move_mock')),
                'description': str(task.get('description', '')),
                'steps': normalized_steps,
            }
        )

    return {
        'queue_name': str(raw.get('queue_name', 'mock_wms_queue')),
        'robot_name': str(raw.get('robot_name', 'my_robot')),
        'tasks': normalized_tasks,
    }


def build_plan(waypoint_bundle, task_bundle):
    waypoints = waypoint_bundle['waypoints']
    plan = []
    for task in task_bundle['tasks']:
        plan.append(
            {
                'task_id': task['task_id'],
                'type': task['type'],
                'description': task['description'],
                'steps': [
                    {
                        **step,
                        'pose': waypoints[step['waypoint']],
                    }
                    for step in task['steps']
                ],
            }
        )
    return plan


def write_report(report_path: Path, report):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write('\n')


def run_dry_run(waypoint_bundle, task_bundle, report_path: Path):
    plan = build_plan(waypoint_bundle, task_bundle)
    step_count = sum(len(task['steps']) for task in plan)

    report = {
        'mode': 'dry-run',
        'generated_at': utc_now_iso(),
        'frame_id': waypoint_bundle['frame_id'],
        'queue_name': task_bundle['queue_name'],
        'robot_name': task_bundle['robot_name'],
        'summary': {
            'task_count': len(plan),
            'step_count': step_count,
            'status': 'validated',
        },
        'tasks': plan,
    }

    write_report(report_path, report)

    print(f'[mock_wms] Dry run validated {len(plan)} tasks / {step_count} steps.')
    print(f'[mock_wms] Report written to: {report_path}')

    for task in plan:
        print(f'  - {task["task_id"]}: {task["description"] or task["type"]}')
        for step in task['steps']:
            pose = step['pose']
            print(
                f'      {step["step_id"]} -> {step["waypoint"]} '
                f'(x={pose["x"]:.2f}, y={pose["y"]:.2f}, yaw={pose["yaw"]:.2f})'
            )


def quaternion_from_yaw(yaw):
    return {
        'z': math.sin(yaw / 2.0),
        'w': math.cos(yaw / 2.0),
    }


def run_execute_mode(waypoint_bundle, task_bundle, report_path: Path, action_name, stop_on_failure):
    import rclpy
    from action_msgs.msg import GoalStatus
    from nav2_msgs.action import NavigateToPose
    from rclpy.action import ActionClient
    from rclpy.node import Node

    class MockWMSDispatcher(Node):
        def __init__(self):
            super().__init__('mock_wms_dispatcher')
            self.frame_id = waypoint_bundle['frame_id']
            self.client = ActionClient(self, NavigateToPose, action_name)

        def wait_for_server(self, timeout_sec=10.0):
            return self.client.wait_for_server(timeout_sec=timeout_sec)

        def send_step(self, task_id, step):
            started_at = utc_now_iso()
            pose = waypoint_bundle['waypoints'][step['waypoint']]

            goal_msg = NavigateToPose.Goal()
            goal_msg.pose.header.frame_id = self.frame_id
            goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
            goal_msg.pose.pose.position.x = pose['x']
            goal_msg.pose.pose.position.y = pose['y']
            quat = quaternion_from_yaw(pose['yaw'])
            goal_msg.pose.pose.orientation.z = quat['z']
            goal_msg.pose.pose.orientation.w = quat['w']

            self.get_logger().info(
                f'Sending {step["step_id"]} for task {task_id} to {step["waypoint"]}'
            )
            send_future = self.client.send_goal_async(goal_msg)
            rclpy.spin_until_future_complete(self, send_future)
            goal_handle = send_future.result()

            if goal_handle is None or not goal_handle.accepted:
                return {
                    'step_id': step['step_id'],
                    'waypoint': step['waypoint'],
                    'status': 'rejected',
                    'started_at': started_at,
                    'finished_at': utc_now_iso(),
                    'pause_sec': step['pause_sec'],
                }

            result_future = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(self, result_future)
            result = result_future.result()
            status_code = result.status
            status_text = GOAL_STATUS_LABELS.get(status_code, f'code_{status_code}')
            succeeded = status_code == GoalStatus.STATUS_SUCCEEDED

            if succeeded and step['pause_sec'] > 0.0:
                self.get_logger().info(
                    f'Pausing {step["pause_sec"]:.1f}s at {step["waypoint"]} for action {step["action"]}'
                )
                time.sleep(step['pause_sec'])

            return {
                'step_id': step['step_id'],
                'waypoint': step['waypoint'],
                'status': status_text,
                'started_at': started_at,
                'finished_at': utc_now_iso(),
                'pause_sec': step['pause_sec'],
            }

    plan = build_plan(waypoint_bundle, task_bundle)
    report = {
        'mode': 'execute',
        'generated_at': utc_now_iso(),
        'frame_id': waypoint_bundle['frame_id'],
        'queue_name': task_bundle['queue_name'],
        'robot_name': task_bundle['robot_name'],
        'action_name': action_name,
        'summary': {
            'task_count': len(plan),
            'step_count': sum(len(task['steps']) for task in plan),
            'status': 'running',
        },
        'tasks': [],
    }

    rclpy.init(args=None)
    node = MockWMSDispatcher()

    try:
        if not node.wait_for_server(timeout_sec=10.0):
            raise RuntimeError(f'NavigateToPose action server not available at {action_name}')

        for task in plan:
            task_record = {
                'task_id': task['task_id'],
                'type': task['type'],
                'description': task['description'],
                'status': 'running',
                'started_at': utc_now_iso(),
                'steps': [],
            }

            task_failed = False
            for step in task['steps']:
                step_result = node.send_step(task['task_id'], step)
                task_record['steps'].append(step_result)
                if step_result['status'] != 'succeeded':
                    task_failed = True
                    if stop_on_failure:
                        break

            task_record['finished_at'] = utc_now_iso()
            task_record['status'] = 'failed' if task_failed else 'succeeded'
            report['tasks'].append(task_record)

            if task_failed and stop_on_failure:
                break

        failed_tasks = sum(1 for task in report['tasks'] if task['status'] != 'succeeded')
        report['summary']['failed_tasks'] = failed_tasks
        report['summary']['completed_tasks'] = len(report['tasks']) - failed_tasks
        report['summary']['status'] = 'failed' if failed_tasks else 'succeeded'
    finally:
        write_report(report_path, report)
        node.destroy_node()
        rclpy.shutdown()

    print(f'[mock_wms] Execute mode finished with status: {report["summary"]["status"]}')
    print(f'[mock_wms] Report written to: {report_path}')


def default_paths():
    root_dir = Path(__file__).resolve().parents[1]
    return {
        'root_dir': root_dir,
        'waypoints': root_dir / 'config' / 'waypoints.json',
        'tasks': root_dir / 'tasks' / 'demo_tasks.json',
        'report': root_dir / 'reports' / 'last_run.json',
    }


def parse_args():
    defaults = default_paths()
    parser = argparse.ArgumentParser(description='Minimal mock WMS task dispatcher.')
    parser.add_argument(
        '--mode',
        choices=('dry-run', 'execute'),
        default='dry-run',
        help='Use dry-run for validation or execute to send sequential Nav2 goals.',
    )
    parser.add_argument(
        '--waypoints',
        type=Path,
        default=defaults['waypoints'],
        help='Path to the waypoint definition file.',
    )
    parser.add_argument(
        '--tasks',
        type=Path,
        default=defaults['tasks'],
        help='Path to the task queue definition file.',
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=defaults['report'],
        help='Path to the generated run report JSON.',
    )
    parser.add_argument(
        '--action-name',
        default='/navigate_to_pose',
        help='Nav2 NavigateToPose action name used in execute mode.',
    )
    parser.add_argument(
        '--continue-on-failure',
        action='store_true',
        help='Continue to the next task after a failed step.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    waypoint_bundle = normalize_waypoints(args.waypoints)
    task_bundle = normalize_task_queue(args.tasks, waypoint_bundle['waypoints'].keys())

    if args.mode == 'dry-run':
        run_dry_run(waypoint_bundle, task_bundle, args.report)
        return

    run_execute_mode(
        waypoint_bundle,
        task_bundle,
        args.report,
        action_name=args.action_name,
        stop_on_failure=not args.continue_on_failure,
    )


if __name__ == '__main__':
    main()
