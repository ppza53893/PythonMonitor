"""PyTaskManager"""
import datetime
import json
import os
import tkinter as tk
import tkinter.ttk as ttk
import traceback
from typing import List, Union

from src import *

TASKMGR_PATH = os.path.split(os.path.abspath(__file__))[0]
ICON = os.path.join(TASKMGR_PATH, 'shared.ico')
TCL_PATH = os.path.join(TASKMGR_PATH, 'azure.tcl')
set_icon(ICON)


class MainWindow(ttk.Frame):
    def __init__(
        self,
        master: tk.Tk,
        width: int,
        height: int,
        ohm: OpenHardwareMonitor) -> None:
        super().__init__(master)
        
        self.master = master
        self.ohm = ohm
        self.height = height
        self.width = width
        self.pack()

        if os.path.exists(TCL_PATH):
            self.master.tk.call("source", TCL_PATH)
            self.master.tk.call("set_theme", "dark")
        
        # init cpu usage
        self.show_hint_message()
        # initialize
        self._initialize_variables()
        # move to default place
        self.move_u()

        # set icon
        if os.path.exists(ICON):
            self.master.iconbitmap(ICON)

        # app settings
        self.master.title('PythonMonitor')
        self.master.attributes("-topmost", self.showtop)
        self.master.protocol("WM_DELETE_WINDOW", self.app_exit)
        self.master.bind('<Control-Key-q>', self.app_exit)
        self.master.bind('<Control-Key-p>', self.switch_topmost)
        self.master.bind('<Control-Key-s>', self.dump_current_status)
        self.master.bind('<Control-Key-h>', self.show_hint_message)
        self.master.bind('<Control-Key-k>', self.move_u)
        self.master.bind('<Control-Key-m>', self.move_d)
        self.master.bind('<Control-Key-j>', self.move_l)
        self.master.bind('<Control-Key-l>', self.move_r)
        self.master.bind('<Control-Key-r>', self.switch_window_transparency)
        self.master.bind('<Control-Key-b>', self.switch_cycle)
        self.master.bind('<Control-Key-t>', self.switch_title)
        self.master.resizable(width=False, height=False)

        # テーブル作成
        self.make_table()

        # 更新用の関数
        self.update()

    def _initialize_variables(self):
        """Initialize.
        """
        # battery
        self.use_battery_mode = self.ohm.select_battery_or_gpu()
        
        # networks
        self.network = Network()
        
        # window
        self.window_width, self.window_height = workingarea()

        # table names
        status = self.ohm.curstatus()
        
        if self.use_battery_mode:
            self.table_names = [
                Name(AC_STATUS, tag='ac'),
                Name(BATTERY, tag='ac', unit='%'),
                Name(BATTERY_STATUS, tag='ac'),
            ]
        else:
            nv = status.GpuNvidia
            self.table_names = [
                Name.from_container(nv.Fan[0].container).update(name=GPU_FAN, tag='gpu_fan'),
                Name.from_container(nv.Power[0].container).update(tag='gpu_power'),
                Name(name=GPU_RAM, tag='gpu_ram', unit='%'),
                Name.from_container(nv.Temperature[0].container).update(name=GPU_TEMP),
            ]
            self.height += 20
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
            Name(NET_SENT, unit='KB/s'),
            Name(NET_RECV, unit='KB/s'),
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
        self.show_status_to_title = True


    def get_full_status(self) -> List[Union[str, int]]:
        """Get current status.

        Collected from:
            - GPU, CPU, Memory data: OpenhardwareMonitor
            - Network System.Net.NetworkInformation
            - Battery System.Forms.SystemInformation.PowerStatus
            - PIDs System.Diagnostics.Process

        Returns:
            List[str, int]: status
        """
        ohm_status = self.ohm.curstatus()
        
        if self.use_battery_mode:
            status = get_battery_status().tolist()
        else:
            nvidia_smi_update()
            status = [
                ohm_status.GpuNvidia.Fan[0].container.value,
                ohm_status.GpuNvidia.Power[0].container.value,
                ohm_status.GpuNvidia.SmallData[1].container.value \
                    / ohm_status.GpuNvidia.SmallData[2].container.value * 100,
                ohm_status.GpuNvidia.Temperature[0].container.value,
            ]

        status += [p.container.value for p in ohm_status.CPU.Temperature]
        status += [p.container.value for p in ohm_status.CPU.Load]
        status += [p.container.value for p in ohm_status.CPU.Clock]
        status += [p.container.value for p in ohm_status.CPU.Power]
        
        if self.show_status_to_title:
            cpu_usage = ohm_status.CPU.Load[0].container.value
            cpu_temp = ohm_status.CPU.Temperature[0].container.value
            title = f'CPU: {cpu_usage:>4.1f}%, Temp: {cpu_temp:>4.1f}°C'
            self.master.title(title)
        
        sent, receive = self.network.get_sent_received()
        _system = [
            c_disk_usage(),
            ohm_status.RAM.Load[0].container.value,
            get_current_pids(),
            sent,
            receive
        ]
        status += _system
        
        return status

    def determine_color(self, name: Name, value: Union[int, float, str]) -> str:
        """
        Set color code.

        Args:
            name (Name): Name object. shuold be in self.table_names.
            value (Union[int, float, str]): value.

        Returns:
            str: color code.
        """
        if name.istag('Temperature'):
            cl = set_temperature_color(value)
        elif name.istag('Load') or name.istag('gpu_ram'):
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

    def make_table(self) -> None:
        """テーブルを作成"""
        self.tree = ttk.Treeview(self.master, height=13, columns=(1,2))

        self.tree.column('#0', width=self.width//2-20)
        self.tree.column(1, width=self.width//2-50)
        self.tree.column(2, width=50)

        self.tree.heading('#0', text='Name')
        self.tree.heading(1, text="Value")
        self.tree.heading(2, text="Unit")

        status = self.get_full_status()

        master_usage_id = ''
        master_power_id = ''
        master_clock_id = ''
        master_temp_id = ''
        
        for index, (name, value) in enumerate(zip(self.table_names, status)):
            insert_kwg = dict(index='end', tags=index, text=name.name, values=(adjust_format(value), name.unit))
            if self.cpu_temp_table.is_children(name):
                id = self.tree.insert(master_temp_id, **insert_kwg)
            elif self.cpu_load_table.is_children(name):
                id = self.tree.insert(master_usage_id, **insert_kwg)
            elif self.cpu_clock_table.is_children(name):
                id = self.tree.insert(master_clock_id, **insert_kwg)
            elif self.cpu_power_table.is_children(name):
                id = self.tree.insert(master_power_id, **insert_kwg)
            else:
                id = self.tree.insert('', **insert_kwg)
            
            if name.name == CPU_LOAD:
                master_usage_id = id
            elif name.name == CPU_POWER:
                master_power_id = id
            elif name.name == CPU_CLOCK:
                master_clock_id = id
            elif name.name == CPU_TEMP:
                master_temp_id = id
            
            self.id_list.append(id)
            self.tree.tag_configure(tagname=index, foreground=self.determine_color(name, value))

        self.tree.pack()

    def update(self) -> None:
        """更新時の挙動"""
        self.check_moveable()

        status = self.get_full_status()
        for index, (table_id, value) in enumerate(zip(self.id_list, status)):
            self.tree.set(table_id, column=1, value=adjust_format(value))
            self.tree.tag_configure(
                tagname=index,
                foreground=self.determine_color(self.table_names[index], value))
            # alert if battery is low or high
            if self.use_battery_mode and index == 1: # BatteryLife
                alert_on_balloontip(value, status[0])
    
        self.master.after(self.cycle, self.update)

    def app_exit(self, *args, **kwargs) -> None:
        """プログラム終了"""
        print('App exit.')
        self.master.destroy()

    def dump_current_status(self, *args, **kwargs) -> None:
        """
        各情報をjson形式で出力(full output)
        """
        status = self.ohm.curstatus()
        print(status, flush=True)

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
            show_message_to_notification(f'ダンプファイルを{fpath}に保存しました。')

    def show_hint_message(self, *args, **kwargs):
        msg = ('使い方:\n\n'
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
            'Ctrl + T ... タイトルにCPU使用率/温度を表示 / 非表示\n\n')

        print(msg)
        info(msg)

    def set_position(self) -> None:
        """位置をセットする"""
        pos_w = self.window_width - self.width
        pos_h = self.window_height - self.height
        frame_border, border = borders()
        if not self.w_bind:
            pos_w -= (frame_border.Width + border.Width)
        if not self.h_bind:
            pos_h -= (frame_border.Height + border.Height)
        print(f'Geometry: `{self.width}x{self.height}+{pos_w}+{pos_h}`.')
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

    def move_u(self, *args, **kwargs) -> None:
        """上へ"""
        if self.h_bind:
            return
        self.window_height = self.height
        self.h_bind = True
        self.set_position()

    def move_d(self, *args, **kwargs) -> None:
        """下へ"""
        if not self.h_bind:
            return
        _, self.window_height = workingarea()
        self.h_bind = False
        self.set_position()

    def move_l(self, *args, **kwargs) -> None:
        """左へ"""
        if self.w_bind:
            return
        self.window_width = self.width
        self.w_bind = True
        self.set_position()

    def move_r(self, *args, **kwargs) -> None:
        """右へ"""
        if not self.w_bind:
            return
        self.window_width, _ = workingarea()
        self.w_bind = False
        self.set_position()

    def switch_topmost(self, *args, **kwargs) -> None:
        """ウィンドウ最前面固定の有効/無効"""
        self.showtop = not self.showtop
        print('Topmost:', self.showtop)
        self.master.attributes("-topmost", self.showtop)

    def switch_window_transparency(self, *args, **kwargs):
        if self.transparent:
            alpha = 1.0
        else:
            alpha = 0.5
        self.transparent = not self.transparent
        print('Transparent:', self.transparent)
        self.master.attributes("-alpha",alpha)

    def switch_cycle(self, *args, **kwargs):
        if self.cycle == 1000:
            self.cycle = 500
        else:
            self.cycle = 1000
        print('Cycle: {:.1f}s'.format(self.cycle/1000))

    def switch_title(self, *args, **kwargs):
        if self.show_status_to_title:
            self.master.title('PythonMonitor')
        self.show_status_to_title = not self.show_status_to_title
        print('Show Status to Title:', self.show_status_to_title)


def start() -> None:
    with OpenHardwareMonitor() as ohm:
        try:
            window = tk.Tk()
            MainWindow(window, 340, 272, ohm)
            window.mainloop()
        except:
            msg = traceback.format_exc()
            show_message_to_notification(msg)
            print('\033[38;5;009m '+msg+'\033[0m')


if __name__ == '__main__':
    check_admin()
    start()
