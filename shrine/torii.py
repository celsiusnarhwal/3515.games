########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
The :class:`Torii` class and related functions.
"""

from __future__ import annotations

from functools import wraps
from types import FunctionType
from typing import Self, Type

from jinja2 import Environment, FileSystemLoader

from support import Assets, Pointer


class Torii(Environment, Pointer):
    """
    The base class for 3515.games' Jinja environments.
    """

    filters_ = {}
    globals_ = {}
    extensions_ = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, extensions=self.extensions_)

        self.filters.update(self.filters_)
        self.globals.update(self.globals_)

    @classmethod
    def _get(cls, pointer: Assets) -> Self:
        return cls(
            loader=FileSystemLoader(pointer / "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @classmethod
    def about(cls):
        return cls._get(Assets.about())

    @classmethod
    def rps(cls):
        return cls._get(Assets.rps())

    @classmethod
    def uno(cls):
        return cls._get(Assets.uno())

    @classmethod
    def chess(cls):
        return cls._get(Assets.chess())

    @classmethod
    def cah(cls):
        return cls._get(Assets.cah())

    @classmethod
    def kurisu(cls):
        return cls._get(Assets.kurisu())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def register_tag(cls: Type) -> Type:
    """
    Decorator for registering a class as a Jinja template tag with :class:`Torii`.

    Examples
    --------
    >>> @register_tag
    ... class SomeClass:
    ...     ...
    """
    Torii.extensions_.append(cls)
    return cls


def register_filter(func: FunctionType) -> FunctionType:
    """
    Decorator for registering a function as a Jinja template filter with :class:`Torii`.

    Examples
    --------
    >>> @register_filter
    ... def some_function():
    ...     ...
    """
    Torii.filters_[func.__name__] = func
    return func


def register_global(
    function: FunctionType = None, *, call: bool = False
) -> FunctionType:
    """
    Decorator for registering a function as a Jinja template global with :class:`Torii`.

    Parameters
    ----------
    call : bool, optional, default: False
        Whether to call the function and register the result as a global.

    Examples
    --------
    >>> @register_global
    ... def some_function():
    ...     ...

    >>> @register_global()  # equivalent to the previous example
    ... def some_function():
    ...     ...

    >>> @register_global(call=True)
    ... def some_function():
    ...     ...
    """

    def decorator(func: FunctionType) -> FunctionType:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        Torii.globals_[func.__name__] = wrapper() if call else wrapper
        return wrapper

    return decorator(function) if function else decorator
