"""Opt-in, state-only Unitree integration."""

from typing import TYPE_CHECKING

__all__ = ['UnitreeStateAdapter']

if TYPE_CHECKING:
    from .state_adapter import UnitreeStateAdapter


def __getattr__(name: str):
    if name == 'UnitreeStateAdapter':
        from .state_adapter import UnitreeStateAdapter

        return UnitreeStateAdapter
    raise AttributeError(name)
