"""Opt-in, state-only Agibot D1 MaxPro integration."""

from typing import TYPE_CHECKING

__all__ = ['AgibotStateAdapter']

if TYPE_CHECKING:
    from .state_adapter import AgibotStateAdapter


def __getattr__(name: str):
    if name == 'AgibotStateAdapter':
        from .state_adapter import AgibotStateAdapter

        return AgibotStateAdapter
    raise AttributeError(name)
