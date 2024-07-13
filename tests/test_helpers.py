from unittest.mock import MagicMock, Mock

from tests.helpers import CustomMockMixin, UnpropagatingMockMixin, synchronize


def test_synchronize():
    """Test the :func:`synchronize` helper function."""

    async def test_func(x: int) -> int:
        if x == 5:
            return 10
        return 0

    assert synchronize(test_func)(5) == 10
    assert synchronize(test_func)(6) == 0


def test_unpropagating_mock_mixin():
    """Test the :class:`UnpropagatingMockMixin` helper class.

    Mocks that inherit from this mixin should not propagate themselves when new attributes are accessed.
    Instead, a general mock (of the generic type) should be returned. By default, this is a :class:`MagicMock`.
    """

    class MyUnpropagatingMock(UnpropagatingMockMixin[MagicMock], Mock): ...

    x = MyUnpropagatingMock(spec_set=str)

    # Test that the `spec_set` works as expected
    assert hasattr(x, "removesuffix")
    assert not hasattr(x, "notastringmethod")

    unpropagated_mock = x.removesuffix()

    # Test that the resulting mock behaves without spec_set
    assert hasattr(unpropagated_mock, "removesuffix")
    assert hasattr(unpropagated_mock, "notastringmethod")


def test_custom_mock_mixin():
    """Test the :class:`CustomMockMixin` helper class.

    This class is very similar to :class:`UnpropagatingMockMixin`, with the only difference being that it
    supports setting ``spec_set`` as a class variable.
    """

    class MyCustomMock(CustomMockMixin[MagicMock], Mock):  # pyright: ignore[reportUnsafeMultipleInheritance]
        spec_set = str

    # Test that the mock really has the `spec_set` of `str` by default
    x = MyCustomMock()
    assert hasattr(x, "removesuffix")
    assert not hasattr(x, "notastringmethod")

    # Explicitly setting `spec_set` on __init__ should take precedence
    y = MyCustomMock(spec_set=int)
    assert not hasattr(y, "removesuffix")
    assert hasattr(y, "to_bytes")
