"""PyTaskManager"""
import argparse
import ctypes
# to STA thread
ctypes.windll.ole32.CoInitialize(None)

import datetime
import json
import os
import time
import traceback
from collections import deque
from contextlib import contextmanager
from functools import partialmethod
from typing import List, Union, Optional

import tkinter as tk
import tkinter.ttk as ttk

from src import *
init_process()

TASKMGR_PATH = os.path.split(os.path.abspath(__file__))[0]
ICON = os.path.join(TASKMGR_PATH, 'app.ico')
set_icon(ICON)


class MainWindow(ttk.Frame):
    class _TitleSwitcher:
        __slots__ = ('_c', '_master', '_gpuenabled', '_batenabled', 'time')
        def __init__(self, master: tk.Tk, gpuenabled: bool, batteryenabled: bool):
            self._c = 0
            self._master = master
            self._gpuenabled = gpuenabled
            self._batenabled = bool(batteryenabled)
            self._time = None
        
        def tostring(self):
            if self._c == 0:
                return 'CPU/Temp'
            elif self._c == 1:
                return 'GPU'
            elif self._c == 2:
                return 'Battery'
            elif self._c == 3:
                return 'Delay'
            elif self._c == 4:
                return f'{PYTASKMGR}'
        
        @property
        def mode(self) -> int:
            return self._c
        
        @property
        def time(self) -> float:
            return self._time
        
        def show(self, text: str):
            if self._c != 4:
                self._master.title(text)
        
        def switch(self):
            self._c += 1
            if self._c == 1 and not self._gpuenabled:
                self._c += 1
            if self._c == 2 and not self._batenabled:
                self._c += 1
            self._c = self._c % 5
        
        @contextmanager
        def watch(self):
            t1 = time.time()
            yield
            t2 = time.time()
            self._time = t2 - t1

    def __init__(self,
                 master: tk.Tk,
                 width: int,
                 height: int,
                 ohm: OpenHardwareMonitor,
                 gpu3d: bool = False,
                 theme: str = 'system') -> None:
        super().__init__(master)
        
        self.master = master
        self.master.call('tk', 'scaling', 1.0)
        self.ohm = ohm
        self.defwidth, self.defheight = width, height
        self.height = height
        self.width = width
        self.gpu3d = gpu3d
        self.theme = theme
        if gpu3d:
            logger.debug('gpu3d is now enabled. Cycles will be slow.')
        self.pack()
                
        # init cpu usage
        #self.show_hint_message()
        # initialize
        self._initialize_variables()
        # move to default place
        self.move_u()

        # set icon
        if os.path.exists(ICON):
            self.master.iconbitmap(ICON)

        # app settings
        self.master.title(PYTASKMGR)
        self.master.attributes("-topmost", self.showtop)
        self.master.protocol("WM_DELETE_WINDOW", self.app_exit)
        self.master.bind(ctrl.q, self.app_exit)
        self.master.bind(ctrl.p, self.switch_topmost)
        self.master.bind(ctrl.s, self.dump_current_status)
        self.master.bind(ctrl.h, self.show_hint_message)
        self.master.bind(ctrl.k, self.move_u)
        self.master.bind(ctrl.m, self.move_d)
        self.master.bind(ctrl.j, self.move_l)
        self.master.bind(ctrl.l, self.move_r)
        self.master.bind(ctrl.r, self.switch_window_transparency)
        self.master.bind(ctrl.b, self.switch_cycle)
        self.master.bind(ctrl.t, self.switch_title)
        self.master.resizable(width=False, height=False)

        # テーブル作成
        self.make_table()

        # 更新用の関数
        self.update()

    def _initialize_variables(self):
        """Initialize variables."""
        # battery
        self.use_battery_mode = self.ohm.select_battery_or_gpu()
        
        # networks
        self.network = Network()
                
        # window
        self.window_width, self.window_height = workingarea()

        # table names
        status = self.ohm()

        # dpi scales
        if self.master.winfo_pixels('1i') != 96:
            *self.dpi_factors, self.current_dpi = getDpiFactor(self.master.winfo_id(), 96)
        else:
            self.dpi_factors = (1,1)
            self.current_dpi = 96

        if self.use_battery_mode is not None:
            if self.use_battery_mode:
                self.table_names = [Name(AC_STATUS, tag='ac'),
                                    Name(BATTERY, tag='ac', unit='%'),
                                    Name(BATTERY_STATUS, tag='ac')]
            else:
                nv = status.GpuNvidia
                self.table_names = [
                    Name.from_container(nv.Fan[0].container).update(name=GPU_FAN, tag='gpu_fan'),
                    Name.from_container(nv.Power[0].container).update(tag='gpu_power'),
                    Name(name=GPU_RAM, tag='gpu_ram', unit='%'),
                    Name.from_container(nv.Temperature[0].container).update(name=GPU_TEMP),
                ]
                self.defheight += 20
        else:
            self.defheight -= 60
            self.table_names = []

        self.width, self.height = map(lambda p: int(p[0]*p[1]), zip((self.defwidth, self.defheight), self.dpi_factors))

        # ttk style
        self.ttk_style = StyleWatch(self.master, min(self.dpi_factors), self.theme)

        # gpus
        if self.gpu3d:
            self.gpu = NetGPU()
            self.gpu.setup()
            self.table_names.append(Name(GPU_LOAD, tag='gpu_load', unit='%'))
            self.height += self._int_factor(20)
        
        # cpus
        self.cpu_temp_table = TableGroup(status.CPU.Temperature, custom_name=CPU_TEMP)
        self.cpu_load_table = TableGroup(status.CPU.Load, custom_name=CPU_LOAD)
        self.cpu_clock_table = TableGroup(status.CPU.Clock, custom_name=CPU_CLOCK)
        self.cpu_power_table = TableGroup(status.CPU.Power, custom_name=CPU_POWER)
        
        self.table_names += self.cpu_temp_table.names
        self.table_names += self.cpu_load_table.names
        self.table_names += self.cpu_clock_table.names
        self.table_names += self.cpu_power_table.names
        
        _system = [
            Name(DISK_USAGE, tag='system', unit='%'),
            Name(MEMORY_USAGE, tag='system', unit='%'),
            Name(RUN_PID),
            Name(NET_SENT, tag='network', unit='KB/s'),
            Name(NET_RECV, tag='network', unit='KB/s'),
        ]
        
        self.table_names += _system

        # is bind or not
        self.h_bind = False
        self.w_bind = False

        # keep tops
        self.showtop = False

        # option
        self.transparent = False

        # update interval
        self.cycle = 1000 # 1s
        
        # table ids
        self.id_list = []
        
        # title 
        self.title_status = self._TitleSwitcher(self.master, self.gpu3d, self.use_battery_mode)
        self.title_text = PYTASKMGR

    def _int_factor(self, value: Union[int, float]) -> int:
        return int(value * min(self.dpi_factors))

    def update_scales(self):
        if dpi_changed(self.master.winfo_id(), self.current_dpi):
            *self.dpi_factors, self.current_dpi = getDpiFactor(self.master.winfo_id(), 96)
            self.width, self.height = map(lambda p: int(p[0]*p[1]), zip((self.defwidth, self.defheight), self.dpi_factors))

            self.ttk_style.dpi_factor = min(self.dpi_factors)
            self.ttk_style.rescale()
            self.ttk_style.apply(force = True)
            self.master.call('tk', 'scaling', 1.0)
            self.master.resizable(width=True, height=True)
            self.master.geometry(f'{self.width}x{self.height}')
            self.master.resizable(width=False, height=False)         

    def get_all_status(self) -> List[Union[str, int]]:
        """現在の状態を取得"""
        ohm_status = self.ohm()
        
        if self.use_battery_mode is not None:
            if self.use_battery_mode:
                status = get_battery_status().tolist()
                if self.title_status.mode == 2:
                    self.title_text = f'Battery: {status[1]:.1f}%'
            else:
                nvidia_smi_update()
                status = [
                    ohm_status.GpuNvidia.Fan[0].value,
                    ohm_status.GpuNvidia.Power[0].value,
                    ohm_status.GpuNvidia.SmallData[1].value \
                        / ohm_status.GpuNvidia.SmallData[2].value * 100,
                    ohm_status.GpuNvidia.Temperature[0].value,
                ]
        else:
            status = []
        if self.gpu3d:
            status += [self.gpu()]
            if self.title_status.mode == 1:
                self.title_text = f'GPU: {status[-1]:.1f}%'

        status += [p.value for p in ohm_status.CPU.Temperature]
        status += [p.value for p in ohm_status.CPU.Load]
        status += [p.value for p in ohm_status.CPU.Clock]
        status += [p.value for p in ohm_status.CPU.Power]
        
        if self.title_status.mode == 0:
            cpu_usage = ohm_status.CPU.Load[0].value
            cpu_temp = ohm_status.CPU.Temperature[0].value
            self.title_text = f'CPU: {cpu_usage:>4.1f}%, Temp: {cpu_temp:>4.1f}°C'
        
        _system = [c_disk_usage(),
                   ohm_status.RAM.Load[0].value,
                   get_current_pids(),
                   *self.network()]
        status += _system
        
        return status

    def make_table(self) -> None:
        """Create table."""
        height = 14
        if self.gpu3d:
            height += 1
        self.tree = ttk.Treeview(self.master, height=height, columns=(1,2))

        self.tree.column('#0', width=self.width//2-self._int_factor(20))
        self.tree.column(1, width=self.width//2-self._int_factor(50))
        self.tree.column(2, width=self._int_factor(50))

        self.tree.heading('#0', text='Name')
        self.tree.heading(1, text="Value")
        self.tree.heading(2, text="Unit")

        status = self.get_all_status()

        master_usage_id = ''
        master_power_id = ''
        master_clock_id = ''
        master_temp_id = ''
        
        self.data_table = {}
        
        for index, (name, value) in enumerate(zip(self.table_names, status)):
            vname = name.tostring()
            
            insert_kwg = dict(index='end', tags=index, text=vname, values=(adjust_format(value), name.unit))
            if self.cpu_temp_table.is_children(name):
                id_ = self.tree.insert(master_temp_id, **insert_kwg)
            elif self.cpu_load_table.is_children(name):
                id_ = self.tree.insert(master_usage_id, **insert_kwg)
            elif self.cpu_clock_table.is_children(name):
                id_ = self.tree.insert(master_clock_id, **insert_kwg)
            elif self.cpu_power_table.is_children(name):
                id_ = self.tree.insert(master_power_id, **insert_kwg)
            else:
                id_ = self.tree.insert('', **insert_kwg)
            
            if vname == CPU_LOAD:
                master_usage_id = id_
            elif vname == CPU_POWER:
                master_power_id = id_
            elif vname == CPU_CLOCK:
                master_clock_id = id_
            elif vname == CPU_TEMP:
                master_temp_id = id_

            if name.tag == 'network':
                ins_value = value if not isinstance(value, str) else 0.0
            else:
                ins_value = value

            self.data_table[id_] = dict(
                name=name,
                type_ = type(ins_value),
                values=deque([0]*29+[ins_value], maxlen=30),
                percentage_range = name.unit == '%' or name.unit == '°C')
            self.id_list.append(id_)
            self.tree.tag_configure(tagname=index, foreground=determine_color(name, value))

        # right-click menu
        self.ttk_style.menu.add_command(label='選択中のデータのグラフを表示',
                                        command=self.create_graph_window,
                                        state=tk.DISABLED)
        self.ttk_style.menu.add_command(label='ヘルプ', command=self.show_hint_message)
        self.ttk_style.menu.add_separator()
        self.ttk_style.menu.add_command(label='終了', command=self.app_exit)
        self.ttk_style.menu.configure(font=('Yu Gothic UI', self._int_factor(11)))

        self.tree.bind('<Button-3>', self.clicked)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def set_position(self) -> None:
        """Set position."""
        pos_w = self.window_width - self.width
        pos_h = self.window_height - self.height
        frame_border, border = borders()
        if not self.w_bind:
            pos_w -= (frame_border.Width + border.Width)
        if not self.h_bind:
            pos_h -= (frame_border.Height + border.Height)
        logger.debug(f'Geometry: `{self.width}x{self.height}+{pos_w}+{pos_h}`.')
        self.master.geometry(f'{self.width}x{self.height}+{pos_w}+{pos_h}')

    def check_moveable(self):
        if self.w_bind and self.h_bind:
            return

        move = False
        # ウィンドウサイズが変わったとき
        wsize, hsize = workingarea()
        if not self.w_bind and wsize != self.window_width:
            self.window_width = wsize
            move = True
        if not self.h_bind and hsize != self.window_height:
            self.window_height = hsize
            move = True
        if move:
            self.set_position()

    def update(self) -> None:
        """Update table."""
        with self.title_status.watch():
            self.check_moveable()
            self.update_scales()
            self.ttk_style.apply()
            
            status = self.get_all_status()
        
            for index, (table_id, value) in enumerate(zip(self.id_list, status)):
                self.tree.set(table_id, column=1, value=adjust_format(value))
                self.tree.tag_configure(
                    tagname=index,
                    foreground=determine_color(self.table_names[index], value))

                if self.table_names[index].tag == 'network':
                    ins_value = value if not isinstance(value, str) else 0
                else:
                    ins_value = value

                self.data_table[table_id]['values'].append(ins_value)
                # alert if battery is low or high
                if self.use_battery_mode and index == 1: # BatteryLife
                    alert_on_balloontip(value, status[0])
        
        if self.title_status.mode == 3:
            c = round(self.cycle/1000, 1)
            self.title_text = f'Cycle: {c}s, Delay: {self.title_status.time:.3f}s'
        # title
        self.title_status.show(self.title_text)
        
        self.master.after(self.cycle, self.update)

    ###################################################################
    #                          event handler                          #
    ###################################################################

    def create_graph_window(self, event: Optional[tk.Event] = None) -> None:
        """
        Create matplotlib window.
        
        Used: self.tree -> self.ttk_style.menu
        """
        show_ids = []
        for table_id in self.tree.selection():
            if self.data_table[table_id]['type_'] is not str:
                show_ids.append(table_id)
        if show_ids:
            create_graph(self, show_ids, ICON)

    def clicked(self, event: Optional[tk.Event] = None) -> None:
        """
        Clicked event.
        
        Used: self.tree
        """
        if self.tree.selection():
            if all(self.data_table[table_id]['type_'] is str for table_id in self.tree.selection()):
                self.ttk_style.menu.entryconfigure(0, state=tk.DISABLED, label='グラフ化できません')
            else:
                self.ttk_style.menu.entryconfigure(0, state=tk.NORMAL, label='選択中のデータのグラフを表示')
        else:
            self.ttk_style.menu.entryconfigure(0, state=tk.DISABLED, label='グラフが選択されていません')
        self.ttk_style.menu.tk_popup(event.x_root, event.y_root)

    def app_exit(self, event: Optional[tk.Event] = None) -> None:
        """Close app."""
        logger.debug('App exit.')
        self.master.destroy()

    def dump_current_status(self, event: Optional[tk.Event] = None) -> None:
        """Dump current status."""
        status = self.ohm()

        _date = datetime.datetime.now().strftime('%Y_%m_%d')
        fpath = os.path.join(TASKMGR_PATH, _date+'_dump.json')
        add_summary = dict(recorded = _date)
        
        if self.use_battery_mode:
            add_summary['Battery Status (all)'] = get_battery_status().tolist()
        try:
            with open(fpath, 'w') as f:
                summary = dict(**status.todict(), **add_summary)
                json.dump(summary, f, indent=4)
        except PermissionError:
            show_message_to_notification('保存に失敗しました。アクセスが拒否されました。')
        else:
            show_message_to_notification(f'データファイルを{fpath}に保存しました。')

    def show_hint_message(self, event: Optional[tk.Event] = None):
        msg = ('コマンド:\n\n'
            'Ctrl + Q ... アプリ終了\n'
            'Ctrl + P ... アプリを最前面に固定 or 解除\n'
            'Ctrl + H ... このヒント画面を表示\n'
            'Ctrl + S ... ダンプファイルを作成\n'
            'Ctrl + K ... ウィンドウを上端に移動\n'
            'Ctrl + M ... ウィンドウを下端に移動\n'
            'Ctrl + J ... ウィンドウを左端に移動\n'
            'Ctrl + L ... ウィンドウを右端に移動\n'
            'Ctrl + R ... ウィンドウを半透明化 or 解除\n'
            'Ctrl + B ... 情報の更新速度を0.5s間隔に変更 / 1s間隔に戻す\n'
            'Ctrl + T ... タイトルのテキストを変更\n'
            '                (CPU/温度, GPU使用率, バッテリー, 遅延、アプリ名)\n\n')
        info(msg)

    def move(self, direction: str, event: Optional[tk.Event] = None) -> None:
        if direction == 'up':
            if self.h_bind:
                return
            self.window_height = self.height
            self.h_bind = True
        elif direction == 'down':
            if not self.h_bind:
                return
            _, self.window_height = workingarea()
            self.h_bind = False
        elif direction == 'left':
            if self.w_bind:
                return
            self.window_width = self.width
            self.w_bind = True
        elif direction == 'right':
            if not self.w_bind:
                return
            self.window_width, _ = workingarea()
            self.w_bind = False
        self.set_position()

    move_u = partialmethod(move, 'up')
    move_d = partialmethod(move, 'down')
    move_l = partialmethod(move, 'left')
    move_r = partialmethod(move, 'right')

    def switch_topmost(self, event: Optional[tk.Event] = None) -> None:
        self.showtop = not self.showtop
        logger.debug(f'Topmost: {self.showtop}')
        self.master.attributes("-topmost", self.showtop)

    def switch_window_transparency(self, event: Optional[tk.Event] = None):
        if self.transparent:
            alpha = 1.0
        else:
            alpha = 0.5
        self.transparent = not self.transparent
        logger.debug(f'Transparent: {self.transparent}')
        self.master.attributes("-alpha",alpha)

    def switch_cycle(self, event: Optional[tk.Event] = None):
        if self.cycle == 1000:
            self.cycle = 500
        else:
            self.cycle = 1000
        logger.debug(f'Cycle: {self.cycle/1000:.1f}s')

    def switch_title(self, event: Optional[tk.Event] = None):
        self.title_status.switch()
        if self.title_status.mode == 4:
            self.title_text = PYTASKMGR
            self.master.title(self.title_text)
        logger.debug(f'Show status to title: {self.title_status.tostring()}')


def start() -> None:
    parser = argparse.ArgumentParser(description=PYTASKMGR)
    parser.add_argument('-g', '--gpu3d', action='store_true', help='GPU使用率(3d)を有効にします。')
    parser.add_argument('-t', '--theme', type=str,
                        choices=['dark', 'light', 'system'], default='system',
                        help='テーマを指定します。systemはOSのデフォルトテーマを使用します。デフォルトはsystemです。')
    
    args = parser.parse_args()
    with OpenHardwareMonitor() as ohm:
        try:
            window = tk.Tk()
            MainWindow(window, 340, 258, ohm, gpu3d = args.gpu3d, theme=args.theme)
            window.mainloop()
        except:
            msg = traceback.format_exc()
            show_message_to_notification(msg)
            logger.error(msg)


if __name__ == '__main__':
    start()
