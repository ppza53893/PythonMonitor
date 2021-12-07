import dataclasses

from typing import Optional, List, Union

from .container import StatusContainer


__all__ = [
    'Name',
    'TableGroup',
    'adjust_format',
    'default_color',
    'set_temperature_color',
    'set_battery_color',
    'set_load_color',
    'set_system_color',]


@dataclasses.dataclass
class Name:
    name: str
    tag: Optional[str] = None
    identifier: Optional[str] = None
    unit: str = ''

    def isname(self, comapre_name: str) -> bool:
        return self.name == comapre_name

    def istag(self, comapre_tag: str) -> bool:
        return self.tag == comapre_tag

    @staticmethod
    def from_container(container: StatusContainer):
        if hasattr(container, 'container'):
            container = container.container
        return Name(
            name = container.name,
            tag = container.type,
            identifier = container.identifier,
            unit = container.format)


@dataclasses.dataclass
class TableGroup:
    container: List[StatusContainer]
    custom_name: Optional[str] = None
    
    def __post_init__(self) -> None:
        self._type = self.container[0].container.type
        self._parent = Name.from_container(self.container[0])
        if len(self.container) > 1:
            self._children = [Name.from_container(c) for c in self.container[1:]]
            self._children_names = [c.name for c in self._children]
            self._children_identifiers = [c.identifier for c in self._children]
        else:
            self._children = []
        
        if self.custom_name is None:
            _p_name = self._type
            if len(self.container) > 1:
                _p_name += 's'
        else:
            _p_name = self.custom_name
        self._parent.name = _p_name
    
    def is_children(self, name: Name) -> bool:
        identifier = name.identifier
        if identifier is None or len(self._children) == 0:
            return False
        else:
            return identifier in self._children_identifiers

    @property
    def parent(self) -> Name:
        return self._parent
    
    @property
    def children(self) -> List[Name]:
        return self._children

    @property
    def parent_name(self) -> str:
        return self._parent.name
    
    @property
    def children_name(self) -> List[str]:
        return self._children_names
    
    @property
    def names(self) -> List[Name]:
        return [self._parent] + self._children


def adjust_format(value):
    if type(value) is float:
        value_str = f'{value:.1f}'
    else:
        value_str = str(value)
    return value_str


def _create_color_code(r: int, g: int, b: int) -> str:
    """
    create color code.
    """
    # raise error if inputs are not in range 0-255
    if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
        raise ValueError("inputs must be in range 0-255")
    return '#{:>2X}{:>02X}{:>02X}'.format(r, g, b)
default_color = _create_color_code(255, 255, 255)


def set_temperature_color(value: int) -> str:
    # clip value 0 to 100
    value = max(0, min(100, value))
    # set value range to [0, 1.]
    value = 1. - value / 100.
    # multiply 255 and convert to int
    value = int(255 * value)
    return _create_color_code(255, value, value)


def set_battery_color(name: 'Name', value: Union[str, int]) -> str:
    if name.isname('Battery'):
        # clip value 0 to 100
        value = max(0, min(100, value))
        # set value range to [0, 1.]
        value = value / 100.
        # multiply 255 and convert to int
        value = int(255 * value)
        if value < 0x80:
            rc = 255
            gc = value * 2
        else:
            rc = round((-0x83*value+0xc001) / 0x7f)
            gc = round((-0x03*value+0x8001) / 0x7f)
        rc = max(0, min(255, rc))
        gc = max(0, min(255, gc))
        return _create_color_code(rc, gc, 0)
    elif name.isname('AC Status'):
        if value == 'Offline':
            return _create_color_code(255, 255, 0)
        elif value == 'Online':
            return _create_color_code(124, 252, 0)
    elif name.isname('Battery Status'):
        if value in ['High', 'Charging', 'Charging(High)']:
            return _create_color_code(124, 252, 0)
        if value in ['Low', 'Charging(Low)']:
            return _create_color_code(255, 255, 0)
        elif value == 'Critical':
            return _create_color_code(255, 0, 0)
    else:
        return default_color


def set_load_color(value: int) -> str:
    return set_temperature_color(value)


def set_system_color(value: int) -> str:
    # clip value 0 to 100
    value = max(0, min(100, value))
    # set value range to [0, 1.]
    value = value / 100.
    # -value^3
    value = -pow(value, 3)
    # add value to 1, then multiply 255 and convert to int
    value = int(255 * (value + 1))
    # clip value 0 to 255
    value = max(0, min(255, value))
    return _create_color_code(255, value, value)