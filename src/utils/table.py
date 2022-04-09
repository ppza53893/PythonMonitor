import enum
import string
import tkinter as tk
import dataclasses
from tkinter import ttk
from typing import List, Optional, Union

from src.systemAPI.gpu import *
from src.systemAPI.registry import system
from src.utils.container import StatusContainer

__all__ = [
    'Name',
    'TableGroup',
    'adjust_format',
    'determine_color',
    'ctrl',
    'StyleWatch']


ALLOWED = ['name', 'tag', 'identifier', 'unit']
ISDARK = True


@enum.unique
class SysColors(enum.IntEnum):
    COLOR_3DDKSHADOW = 21
    COLOR_3DFACE = 15
    COLOR_BTNTEXT = 18
    COLOR_GRAYTEXT = 17
    COLOR_HIGHLIGHT = 13
    COLOR_HIGHLIGHTTEXT = 14
    COLOR_HOTLIGHT = 26
    COLOR_WINDOW = 5
    COLOR_WINDOWTEXT = 9


class _Ctrl:
    __slots__ = tuple(string.ascii_lowercase)
    def __init__(self):
        for s in string.ascii_lowercase:
            setattr(self, s, f'<Control-Key-{s}>')
ctrl = _Ctrl()


@dataclasses.dataclass
class Name:
    name: str
    tag: Optional[str] = None
    identifier: Optional[str] = None
    unit: str = ''
    
    def tostring(self):
        return self.name

    def isname(self, comapre_name: str) -> bool:
        return self.name == comapre_name

    def istag(self, comapre_tag: str) -> bool:
        return self.tag == comapre_tag
    
    def update(self, **kwargs) -> 'Name':
        for key in kwargs:
            if key not in ALLOWED:
                raise ValueError(f'{key} is not supported.')
            setattr(self, key, kwargs[key])
        return self

    @staticmethod
    def from_container(container: StatusContainer):
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
        self._parent = self._parent.update(name = _p_name)
    
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
    return '#{:>02X}{:>02X}{:>02X}'.format(r, g, b)


default_color = '#FFFFFF'


def set_temperature_color(value: int) -> str:
    # clip value 0 to 100
    value = max(0, min(100, value))
    value = 1. - value / 100.
    if ISDARK:
        value = int(255 * value)
        return _create_color_code(255, value, value)
    else:
        value = int(0xCC * value)
        return _create_color_code(value, 0, 0)


def set_battery_color(name: 'Name', value: Union[str, int]) -> str:
    if name.isname('Battery'):
        # clip value 0 to 100
        value = max(0, min(100, value))
        # set value range to [0, 1.]
        value = value / 100.
        # multiply 255 and convert to int
        value = int(255 * value)
        if ISDARK:
            if value < 0x80:
                rc = 255
                gc = value * 2
            else:
                rc = round((-131*value+49153) / 127)
                gc = round((-3*value+32769) / 127)
        else:
            # bit complex
            if value < 0x80:
                rc = round((-0.9296875*value+288.0703125))
                gc = value * 0xAA
            else:
                rc = round((-1.328125*value+388.671875))
                gc = 0xAA
        rc = max(0, min(255, rc))
        gc = max(0, min(255, gc))
        return _create_color_code(rc, gc, 0)
    elif name.isname('AC Status'):
        if value == 'Offline':
            return "#FFFF00" if ISDARK else "#AAAA00"
        elif value == 'Online':
            return "#7CfC00" if ISDARK else "#AAAA00"
    elif name.isname('Battery Status'):
        if value in ['High', 'Charging', 'Charging(High)']:
            return "#7CfC00" if ISDARK else "#00AA00"
        if value in ['Low', 'Charging(Low)']:
            return "#FFFF00" if ISDARK else "#AAAA00"
        elif value == 'Critical':
            return "#FF0000" if ISDARK else "#CC0000"
    else:
        return default_color


def set_load_color(value: int) -> str:
    return set_temperature_color(value)


def set_system_color(value: int) -> str:
    value = max(0, min(100, value)) / 100.
    if ISDARK:
        value = int(255 * (1-pow(value, 3)))
        value = max(0, min(255, value))
        return _create_color_code(255, value, value)
    else:
        value = int(0xCC * (1-pow(value, 3)))
        value = max(0, min(0xCC, value))
        return _create_color_code(value, 0, 0)


def set_nvgpu_power_color(value: float) -> str:
    power_limit = gpu_power_limit()
    if type(power_limit) is float:
        value_p = value / power_limit * 100
        return set_temperature_color(value_p)
    else:
        return default_color


def set_nvgpu_fan_color() -> str:
    fan_speed = gpu_fan_speed()
    if type(fan_speed) is float:
        return set_temperature_color(fan_speed)
    else:
        return default_color


def determine_color(name: Name, value: Union[int, float, str]) -> str:
    if name.istag('Temperature'):
        cl = set_temperature_color(value)
    elif name.istag('Load') or name.istag('gpu_ram') or name.istag('gpu_load'):
        cl = set_load_color(value)
    elif name.istag('gpu_power'):
        cl = set_nvgpu_power_color(value)
    elif name.istag('gpu_fan'):
        cl = set_nvgpu_fan_color()
    elif name.istag('ac'):
        cl = set_battery_color(name, value)
    elif name.istag('system'):
        cl = set_system_color(value)
    else:
        cl = default_color
    
    return cl


class StyleWatch():
    FONT = 'Yu Gothic UI'
    
    @dataclasses.dataclass
    class ColorHolder:
        foreground: str
        background: str
        heading: str

    def __init__(self,
                 master: tk.Tk=None,
                 dpi_factor: float=1.,
                 theme: str = 'system'):
        if master is None:
            master = tk.Tk()
        self.master = master
        self.dpi_factor = dpi_factor
        if theme == 'system':
            self.current_mode = system.is_dark_mode()
            self.syscolor = system.colorization_color()
        else:
            self.current_mode = theme == 'dark'
            self.syscolor = '#0077cc' if theme == 'dark' else '#00aaff'
        self.theme = theme

        self.style = ttk.Style(master)
        self.style.theme_use('default')
        self.menu = tk.Menu(self.master, tearoff=False)
        self.colors = self.choose_color()
        self._init_styling()
        self.apply(True)

    def rescale(self):
        self.style.configure("Treeview",
                                font=(self.FONT, self.scaleto(12)),
                                rowheight=self.scaleto(20))
        self.style.configure("Treeview.Heading",
                                font=(self.FONT, self.scaleto(12)),
                                height=self.scaleto(20))
        self.menu.configure(font=(self.FONT, self.scaleto(11)), borderwidth=0, border=0, relief='flat')

    def _init_styling(self):
        self.rescale()
        self.style.theme_use('default')
        self.style.layout('Treeview.Heading',
                            [('Treeheading.cell', {'sticky': 'ewns', 'border': '5'}),
                            ('Treeheading.border', {'sticky': 'nswe', 'children': [
                                ('Treeheading.padding', {'sticky': 'nswe', 'children': [
                                    ('Treeheading.image', {'side': 'right', 'sticky': ''}),
                                    ('Treeheading.text', {'sticky': 'we'})]}
                                )]}
                            )]
                            )
        # remove dot lines
        self.style.layout('Treeview.Item',
                            [('Treeitem.padding',
                            {'children': [
                                ('Treeitem.indicator', {'side': 'left', 'sticky': ''}),
                                ('Treeitem.image', {'side': 'left', 'sticky': ''}),
                                ('Treeitem.text', {'side': 'left', 'sticky': ''})],
                                'sticky': 'nswe'})
                            ]
                            )

    def apply(self, force: bool=False):
        if not force:
            if self.theme != 'system':
                return
            t = system.colorization_color()
            s = system.is_dark_mode()
            if t == self.syscolor and s == self.current_mode:
                return
            self.syscolor = t
            self.current_mode = s
        self.colors = self.choose_color()
        self.style.configure('.',
                             font=(self.FONT, self.scaleto(12)),
                             foreground = self.colors.foreground,
                             background=self.colors.background,
                             insertcolor=self.colors.foreground,
                             selectforeground=self.syscolor,
                             selectbackground=self.colors.background,
                             throughcolor=self.colors.background,
                             fieldbackground=self.syscolor,
                             borderwidth=0,
                             relief = tk.SOLID,
                             )
        self.master.tk_setPalette(
            background=self.style.lookup('.', 'background'),
            foreground=self.style.lookup('.', 'foreground'),
            selectBackground=self.style.lookup('.', 'selectbackground'),
            selectForeground=self.style.lookup('.', 'selectforeground'),
            highlightColor=self.style.lookup('.', 'fieldbackground'))
        self.style.configure('Treeview', background=self.colors.background, fieldbackground=self.colors.background)
        self.style.configure('Treeview.Heading',
                             background=self.colors.heading,
                             foreground=self.colors.foreground)
        self.style.configure('Treeview.Item', padding=(2, 0, 0, 0))
        self.style.map('Treeview',
                       background=[('selected', self.style.lookup('.', 'selectforeground'))],
                       foreground=[('selected', self.style.lookup('.', 'foreground'))])
        self.style.map('Treeview.Heading', background=[('selected', self.colors.heading)])
        self.menu.configure(
            activebackground=self.colors.heading,
            activeforeground=self.colors.foreground,
            background=self.colors.background,
            disabledforeground=self.colors.heading,
            foreground=self.colors.foreground,
            )
    
    def scaleto(self, value: int):
        return int(value * self.dpi_factor)
    
    def choose_color(self):
        global default_color, ISDARK
        if self.theme == 'system':
            isdarkmode = system.is_dark_mode()
        elif self.theme == 'dark':
            isdarkmode = True
        else:
            isdarkmode = False

        if isdarkmode:
            holder = self.ColorHolder("#ffffff", "#393939", "#707070")
            ISDARK = True
        else:
            holder = self.ColorHolder("#000000", "#ffffff", "#CCCCCC")
            ISDARK = False
        default_color = holder.foreground
        return holder
