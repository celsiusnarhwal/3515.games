########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

from functools import wraps
from types import FunctionType
from typing import Self, Type

from jinja2 import Environment, FileSystemLoader

from support import Assets


class Torii(Environment):
    """
    The base class for 3515.games' Jinja2 environments.
    """

    custom_filters = {}
    custom_globals = {}
    tags = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters.update(self.custom_filters)
        self.globals.update(self.custom_globals)

        for tag in self.tags:
            self.add_extension(tag)

    @classmethod
    def _get_env(cls, pointer: Assets) -> Self:
        return cls(
            loader=FileSystemLoader(pointer / "templates"), trim_blocks=True, lstrip_blocks=True
        )

    @classmethod
    def about(cls):
        return cls._get_env(Assets.about())

    @classmethod
    def rps(cls):
        return cls._get_env(Assets.rps())

    @classmethod
    def uno(cls):
        return cls._get_env(Assets.uno())

    @classmethod
    def chess(cls):
        return cls._get_env(Assets.chess())

    @classmethod
    def cah(cls):
        return cls._get_env(Assets.cah())

    @classmethod
    def kurisu(cls):
        return cls._get_env(Assets.kurisu())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def register_tag(cls: Type) -> Type:
    """
    Decorator for registering a class as a Jinja2 template tag with :class:`Torii`.

    Examples
    --------
    >>> @register_tag
    ... class SomeTag:
    ...     ...
    """
    Torii.tags.append(cls)
    return cls


def register_filter(func: FunctionType) -> FunctionType:
    """
    Decorator for registering a function as a Jinja2 template filter with :class:`Torii`.

    Examples
    --------
    >>> @register_filter
    ... def some_function():
    ...     ...
    """
    Torii.custom_filters[func.__name__] = func
    return func


def register_global(
    _function: FunctionType = None, *, call: bool = False
) -> FunctionType:
    """
    Decorator for registering a function as a Jinja2 template global with :class:`Torii`.

    Parameters
    ----------
    call : bool, optional, default: False
        Whether to call the function and register the result as a global.

    Notes
    -----
    The ``_function`` parameter allows the decorator to be called without parentheses, as with :func:`register_filter`.
    This means that the following uses of this decorator are all valid:

    >>> @register_global
    ... def some_function():
    ...     ...

    >>> @register_global()
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

        Torii.custom_globals[func.__name__] = wrapper() if call else wrapper
        return wrapper

    return decorator if not _function else decorator(_function)
