"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Literal, Optional, TypeVar, Union, ClassVar

from .item import Item
from .text_display import TextDisplay
from ..enums import ComponentType
from ..utils import MISSING, get as _utils_get

if TYPE_CHECKING:
    from typing_extensions import Self

    from .view import LayoutView
    from ..components import SectionComponent

V = TypeVar('V', bound='LayoutView', covariant=True)

__all__ = ('Section',)


class Section(Item[V]):
    """Represents a UI section.

    This is a top-level layout component that can only be used on :class:`LayoutView`

    .. versionadded:: 2.6

    Parameters
    ----------
    *children: Union[:class:`str`, :class:`TextDisplay`]
        The text displays of this section. Up to 3.
    accessory: :class:`Item`
        The section accessory.
    row: Optional[:class:`int`]
        The relative row this section belongs to. By default
        items are arranged automatically into those rows. If you'd
        like to control the relative positioning of the row then
        passing an index is advised. For example, row=1 will show
        up before row=2. Defaults to ``None``, which is automatic
        ordering. The row number must be between 0 and 39 (i.e. zero indexed)
    id: Optional[:class:`int`]
        The ID of this component. This must be unique across the view.
    """

    __discord_ui_section__: ClassVar[bool] = True
    __discord_ui_update_view__: ClassVar[bool] = True

    __slots__ = (
        '_children',
        'accessory',
    )

    def __init__(
        self,
        *children: Union[Item[V], str],
        accessory: Item[V],
        row: Optional[int] = None,
        id: Optional[int] = None,
    ) -> None:
        super().__init__()
        self._children: List[Item[V]] = []
        if children is not MISSING:
            if len(children) > 3:
                raise ValueError('maximum number of children exceeded')
            self._children.extend(
                [c if isinstance(c, Item) else TextDisplay(c) for c in children],
            )
        self.accessory: Item[V] = accessory
        self.row = row
        self.id = id

    @property
    def type(self) -> Literal[ComponentType.section]:
        return ComponentType.section

    @property
    def children(self) -> List[Item[V]]:
        """List[:class:`Item`]: The list of children attached to this section."""
        return self._children.copy()

    @property
    def width(self):
        return 5

    def _is_v2(self) -> bool:
        return True

    # Accessory can be a button, and thus it can have a callback so, maybe
    # allow for section to be dispatchable and make the callback func
    # be accessory component callback, only called if accessory is
    # dispatchable?
    def is_dispatchable(self) -> bool:
        return self.accessory.is_dispatchable()

    def is_persistent(self) -> bool:
        return self.is_dispatchable() and self.accessory.is_persistent()

    def walk_children(self) -> Generator[Item[V], None, None]:
        """An iterator that recursively walks through all the children of this section.
        and it's children, if applicable.

        Yields
        ------
        :class:`Item`
            An item in this section.
        """

        for child in self.children:
            yield child
        yield self.accessory

    def _update_children_view(self, view) -> None:
        self.accessory._view = view

    def add_item(self, item: Union[str, Item[Any]]) -> Self:
        """Adds an item to this section.

        This function returns the class instance to allow for fluent-style
        chaining.

        Parameters
        ----------
        item: Union[:class:`str`, :class:`Item`]
            The item to append, if it is a string it automatically wrapped around
            :class:`TextDisplay`.

        Raises
        ------
        TypeError
            An :class:`Item` or :class:`str` was not passed.
        ValueError
            Maximum number of children has been exceeded (3).
        """

        if len(self._children) >= 3:
            raise ValueError('maximum number of children exceeded')

        if not isinstance(item, (Item, str)):
            raise TypeError(f'expected Item or str not {item.__class__.__name__}')

        item = item if isinstance(item, Item) else TextDisplay(item)
        item._view = self.view
        item._parent = self
        self._children.append(item)

        if self._view and getattr(self._view, '__discord_ui_layout_view__', False):
            self._view.__total_children += 1

        return self

    def remove_item(self, item: Item[Any]) -> Self:
        """Removes an item from this section.

        This function returns the class instance to allow for fluent-style
        chaining.

        Parameters
        ----------
        item: :class:`TextDisplay`
            The item to remove from the section.
        """

        try:
            self._children.remove(item)
        except ValueError:
            pass
        else:
            if self._view and getattr(self._view, '__discord_ui_layout_view__', False):
                self._view.__total_children -= 1

        return self

    def get_item_by_id(self, id: int, /) -> Optional[Item[V]]:
        """Gets an item with :attr:`Item.id` set as ``id``, or ``None`` if
        not found.

        .. warning::

            This is **not the same** as ``custom_id``.

        Parameters
        ----------
        id: :class:`int`
            The ID of the component.

        Returns
        -------
        Optional[:class:`Item`]
            The item found, or ``None``.
        """
        return _utils_get(self._children, id=id)

    def clear_items(self) -> Self:
        """Removes all the items from the section.

        This function returns the class instance to allow for fluent-style
        chaining.
        """
        if self._view and getattr(self._view, '__discord_ui_layout_view__', False):
            self._view.__total_children -= len(self._children) + 1  # the + 1 is the accessory

        self._children.clear()
        return self

    @classmethod
    def from_component(cls, component: SectionComponent) -> Self:
        from .view import _component_to_item  # >circular import<

        return cls(
            *[_component_to_item(c) for c in component.components],
            accessory=_component_to_item(component.accessory),
            id=component.id,
        )

    def to_component_dict(self) -> Dict[str, Any]:
        data = {
            'type': self.type.value,
            'components': [
                c.to_component_dict()
                for c in sorted(
                    self._children,
                    key=lambda i: i._rendered_row or sys.maxsize,
                )
            ],
            'accessory': self.accessory.to_component_dict(),
        }
        if self.id is not None:
            data['id'] = self.id
        return data
