from __future__ import annotations

import asyncio
import unittest.mock
from typing import Any, ClassVar, Generic, TYPE_CHECKING, TypeVar

from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

T = TypeVar("T")
P = ParamSpec("P")
T_Mock = TypeVar("T_Mock", bound=unittest.mock.Mock)

__all__ = [
    "synchronize",
    "UnpropagatingMockMixin",
    "CustomMockMixin",
]


def synchronize(f: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, T]:
    """Take an asynchronous function, and return a synchronous alternative.

    This is needed because we sometimes want to test asynchronous behavior in a synchronous test function,
    where we can't simply await something. This function uses `asyncio.run` and generates a wrapper
    around the original asynchronous function, that awaits the result in a blocking synchronous way,
    returning the obtained value.
    """

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


class UnpropagatingMockMixin(Generic[T_Mock]):
    """Provides common functionality for our :class:`~unittest.mock.Mock` classes.

    By default, mock objects propagate themselves by returning a new instance of the same mock
    class, with same initialization attributes. This is done whenever we're accessing new
    attributes that mock class.

    This propagation makes sense for simple mocks without any additional restrictions, however when
    dealing with limited mocks to some ``spec_set``, it doesn't usually make sense to propagate
    those same ``spec_set`` restrictions, since we generally don't have attributes/methods of a
    class be of/return the same class.

    This mixin class stops this propagation, and instead returns instances of specified mock class,
    defined in :attr:`.child_mock_type` class variable, which is by default set to
    :class:`~unittest.mock.MagicMock`, as it can safely represent most objects.

    .. note:
        This propagation handling will only be done for the mock classes that inherited from this
        mixin class. That means if the :attr:`.child_mock_type` is one of the regular mock classes,
        and the mock is propagated, a regular mock class is returned as that new attribute. This
        regular class then won't have the same overrides, and will therefore propagate itself, like
        any other mock class would.

        If you wish to counteract this, you can set the :attr:`.child_mock_type` to a mock class
        that also inherits from this mixin class, perhaps to your class itself, overriding any
        propagation recursively.
    """

    child_mock_type: T_Mock = unittest.mock.MagicMock

    # Since this is a mixin class, we can access some attributes defined in mock classes safely.
    # Define the types of these variables here, for proper static type analysis.
    _mock_sealed: bool
    _extract_mock_name: Callable[[], str]

    def _get_child_mock(self, **kwargs: object) -> T_Mock:
        """Make :attr:`.child_mock_type`` instances instead of instances of the same class.

        By default, this method creates a new mock instance of the same original class, and passes
        over the same initialization arguments. This overrides that behavior to instead create an
        instance of :attr:`.child_mock_type` class.
        """
        # Mocks can be sealed, in which case we wouldn't want to allow propagation of any kind
        # and rather raise an AttributeError, informing that given attr isn't accessible
        if self._mock_sealed:
            mock_name = self._extract_mock_name()
            obj_name = f"{mock_name}.{kwargs['name']}" if "name" in kwargs else f"{mock_name}()"
            raise AttributeError(f"Can't access {obj_name}, mock is sealed.")

        # Propagate any other children as the `child_mock_type` instances
        # rather than `self.__class__` instances
        return self.child_mock_type(**kwargs)


class CustomMockMixin(UnpropagatingMockMixin[T_Mock], Generic[T_Mock]):
    """Provides common functionality for our custom mock types.

    * Stops propagation of same ``spec_set`` restricted mock in child mocks
      (see :class:`.UnpropagatingMockMixin` for more info)
    * Allows using the ``spec_set`` attribute as class attribute
    """

    spec_set: ClassVar[object] = None

    def __init__(self, **kwargs: object):
        # If `spec_set` is explicitly passed, have it take precedence over the class attribute.
        #
        # Although this is an edge case, and there usually shouldn't be a need for this.
        # This is mostly for the sake of completeness, and to allow for more flexibility.
        if "spec_set" in kwargs:
            spec_set = kwargs.pop("spec_set")
        else:
            spec_set = self.spec_set

        super().__init__(spec_set=spec_set, **kwargs)  # pyright: ignore[reportCallIssue]  # Mixin class, this __init__ is valid
