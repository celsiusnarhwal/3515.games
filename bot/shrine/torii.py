########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
:class:`Torii` and company.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps

from jinja2 import Environment, FileSystemLoader, Template

from keyboard import *
from support import Assets


class Torii(Environment):
    """
    Base class for Jinja environments.
    """

    filters_: ClassVar[dict[str, Callable]] = {}
    globals_: ClassVar[dict[str, Any]] = {}
    extensions_: ClassVar[list[type]] = []

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, **kwargs, extensions=self.extensions_, enable_async=True
        )
        self.filters.update(self.filters_)
        self.globals.update(self.globals_)

    @classmethod
    def _get(cls, pointer: Assets) -> Self:
        return cls(loader=FileSystemLoader(pointer / "templates"))

    @classmethod
    def misc(cls) -> Self:
        return cls._get(Assets.misc())

    @classmethod
    def rps(cls) -> Self:
        return cls._get(Assets.rps())

    @classmethod
    def uno(cls) -> Self:
        return cls._get(Assets.uno())

    @classmethod
    def chess(cls) -> Self:
        return cls._get(Assets.chess())

    @classmethod
    def cah(cls) -> Self:
        return cls._get(Assets.cah())

    @classmethod
    def kurisu(cls) -> Self:
        return cls._get(Assets.kurisu())

    def get_template(self, name: str, *args, **kwargs) -> Shintai:
        template = super().get_template(name, *args, **kwargs)
        template.__class__ = Shintai
        return template

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Shintai(Template):
    """
    Base class for Jinja templates rendered by :class:`Torii`.
    """

    def render(self, *args, **kwargs) -> str:
        return super().render(*args, **kwargs).strip("\n")

    def slender(self, *args, **kwargs) -> str:
        @contextmanager
        def slim():
            trim, lstrip = self.environment.trim_blocks, self.environment.lstrip_blocks
            self.environment.trim_blocks = self.environment.lstrip_blocks = True
            yield
            self.environment.trim_blocks, self.environment.lstrip_blocks = trim, lstrip

        with slim():
            return self.render(*args, **kwargs)


def register_tag(cls: type) -> type:
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


def register_filter(func: Callable) -> Callable:
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


def register_global(function: Callable = None, *, call: bool = False) -> Callable:
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

    def decorator(func: function) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        Torii.globals_[func.__name__] = wrapper() if call else wrapper
        return wrapper

    return decorator(function) if function else decorator
