"""Opt-in, state-only DEEPRobotics integration."""

from typing import TYPE_CHECKING

__all__ = ['DeepRoboticsStateAdapter']

if TYPE_CHECKING:
    from .state_adapter import DeepRoboticsStateAdapter


def __getattr__(name: str):
    if name == 'DeepRoboticsStateAdapter':
        from .state_adapter import DeepRoboticsStateAdapter

        return DeepRoboticsStateAdapter
    raise AttributeError(name)
