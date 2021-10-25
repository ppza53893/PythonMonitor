"""PyTaskManager"""
import datetime
import functools
import json
import nt  # type: ignore
import os
import sys
import time
import tkinter as tk
import tkinter.ttk as ttk
from typing import Callable, List, Tuple, Union

import cs_ops
from ohm_ops import OpenHardWareMonitor


TASKMGR_PATH = os.path.split(os.path.abspath(__file__))[0]
ICON = os.path.join(TASKMGR_PATH, 'shared.ico')
TCL_PATH = os.path.join(TASKMGR_PATH, 'azure.tcl')
NETOWORK = cs_ops.get_networks()
RECURSIVE_LOOP = 0

show_notification: Callable[[str], None] = functools.partial(
    cs_ops.show_notification,
    app_icon=ICON)


class MainWindow(ttk.Frame):
    COLOR_MAX = 255
    BATTERY_ALERT_MIN: int = 35
    BATTERY_ALERT_MAX: int = 95
    MAX_GPU_POWER = None

    def __init__(
        self,
        master: tk.Tk,
        width: int=640,
        height: int=480,
        ohm: OpenHardWareMonitor=None) -> None:
        super().__init__(master)
        self.master = master
        self.pack()

        if os.path.exists(TCL_PATH):
            self.master.tk.call("source", TCL_PATH)
            self.master.tk.call("set_theme", "dark")
        
        # ohm
        self.ohm = ohm

        # some
        self.battery_id = ''
        self.battery_full = False        
        self.battery_warn = False
        self.cycle = 1000 # 1s

        # if has battery & has nvidia gpu
        bcs = cs_ops.get_battery_status()
        unsupported = ['NoSystemBattery', 'Unknown']
        if self.ohm.has_nvidia_gpu and bcs not in unsupported:
            result = cs_ops.hint_yesno('Nvidia GPUを検出しました。バッテリ―状態の代わりに表示しますか?')
            self.use_battery = result == cs_ops.ans_yes
        else:
            # desktop or tablet
            self.use_battery = bcs not in unsupported
        
        # define name
        self.name = self.get_name()
        self.bcs_name_fix = cs_ops.bcs_name_fix()

        # screen size
        self.window_width, self.window_height = cs_ops.workingarea()

        # tkinter window size
        self.height = height
        self.width = width

        # is bind or not
        self.h_bind = False
        self.w_bind = False

        # keep tops
        self.showtop = False

        # option
        self.transparent = False
        
        # init cpu usage
        self.cpu = cs_ops.cpu_usage()
        self.show_hint_message()

        # networks
        self.network = cs_ops.get_networks()
        self.wifi_sent, self.wifi_receive = self.get_wifi_usage()
        self.time_temp = time.time()
  
        # master
        self.set_position()
        # self.master.overrideredirect(True)
        if ICON is not None and os.path.exists(ICON):
            self.master.iconbitmap(ICON)
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
        
        # initial title
        self.master.title('Process')
        self.master.attributes("-topmost", self.showtop)

        # lock
        self.master.resizable(width=False, height=False)


        # move to up
        self.move_u()

        # 表示する単位の設定
        self.set_format()

        # テーブル作成
        self.make_table()

        # 更新用の関数
        self.update()


    def get_wifi_usage(self) -> Tuple[int, int]:
        if self.network.isempty:
            return -1, -1
        adapter = self.network.adapter
        stats = adapter.GetIPv4Statistics()
        return stats.BytesSent, stats.BytesReceived

    def get_name(self) -> List[str]:
        if not self.use_battery:
            self._init_name = ['GPU fan', 'GPU power', 'GPU temperature']
            self.type = 'gpu'
        else:
            self._init_name = ['AC status','Battery', 'Battery status']
            self.type = 'ac'

        self._cpu_usage: List[str] = ['CPU usage']+\
            [f'CPU #{i+1} usage' for i in range(cs_ops.num_processors())]
        self._cpu_freq: List[str] = ['CPU bus'] +\
            [f'CPU #{i+1} clock' for i in range(self.ohm.i_cpu_size('Clock')-1)]
        self._cpu_power: List[str] = ['CPU power', 'CPU (cores) power'] +\
            [f'CPU #{i+1} power' for i in range(self.ohm.i_cpu_size('Power')-2)]

        temps = self.ohm.i_cpu_size('Temperature')
        self._cpu_temp = ['CPU temperature']
        if temps > 1:
            self._cpu_temp += [f'CPU #{i+1} temperature' for i in range(temps - 1)]
        cpus = self._cpu_temp + self._cpu_usage + self._cpu_freq + self._cpu_power

        self._system = [
            'Disk usage', 'Memory',
            'Running PIDs',
            'WiFi usage (In)',
            'WiFi usage (Out)']

        self.exclude = self._cpu_freq + self._cpu_power +\
            ['WiFi usage (In)', 'WiFi usage (Out)'] + ['GPU fan', 'GPU power']
        return self._init_name + cpus + self._system

    def set_format(self) -> None:
        self.unit = []
        for name in self.name:
            if name in ['Running PIDs', 'AC status', 'Battery status']:
                self.unit.append('')
            elif name in ['WiFi usage (In)', 'WiFi usage (Out)']:
                self.unit.append('KB/s')
            elif name in ['GPU temperature', 'CPU temperature']:
                self.unit.append('°C')
            elif name in self._cpu_power + ['GPU power']:
                self.unit.append('W')
            elif name in self._cpu_freq:
                self.unit.append('MHz')
            elif name == 'GPU fan':
                self.unit.append('RPM')
            else:
                self.unit.append('%')

    def set_position(self) -> None:
        """位置をセットする"""
        pos_w = self.window_width - self.width
        pos_h = self.window_height - self.height
        frame_border, border = cs_ops.borders()
        if not self.w_bind:
            pos_w -= (frame_border.Width + border.Width)
        if not self.h_bind:
            pos_h -= (frame_border.Height + border.Height)
        print(f'Geometry: `{self.width}x{self.height}+{pos_w}+{pos_h}`.')
        self.master.geometry(f'{self.width}x{self.height}+{pos_w}+{pos_h}')

    def get_status(self) -> List[Union[str, int]]:
        """
        各情報を取得する
        """
        # OHMからの情報
        current_status = self.ohm.curstatus()

        if self.type == 'ac':
            # バッテリー情報
            ac_info = cs_ops.get_battery_status().tolist()
            init_info= [ac_info[0], ac_info[2], ac_info[1]]
        elif self.type == 'gpu':
            # gpu
            gpu_info = current_status.GpuNvidia
            init_info = [
                gpu_info.Fan[0].container.value,
                gpu_info.Power[0].container.value,
                gpu_info.Temperature[0].container.value]

        # CPU温度
        try:
            temperature = [t.container.value for t in current_status.CPU.Temperature]
        except:
            # 無ければ
            temperature = ['NaN']

        # cpu使用率
        processes_cpu = [cpu.NextValue() for cpu in self.cpu]

        self.master.title(
            'CPU: {:>4.1f}%, Temp: {:>4.1f}°C'.format(processes_cpu[0], temperature[0]))

        # クロック周波数
        try:
            processes_cpu += [p.container.value for p in current_status.CPU.Clock]
        except KeyError:
            processes_cpu += ['NaN']

        # 電力
        try:
            processes_cpu += [p.container.value for p in current_status.CPU.Power]
        except KeyError:
            processes_cpu += ['NaN']
        
        # その他
        total, free = nt._getdiskusage('c:\\')
        others = [
            round(100*(total - free) / total, 1),  # Cドライブ使用量
            cs_ops.memory_usage(),                 # RAM使用量 
            len(cs_ops.get_current_pids())]          # PID数

        # Wifi使用量(MB/s)
        cur_sent, cur_recv = self.get_wifi_usage()
        _time = time.time()
        time_diff = _time - self.time_temp
        if cur_sent >= 0:
            sent_ps = (cur_sent - self.wifi_sent) / 1024 * time_diff
            resc_ps = (cur_recv - self.wifi_receive) / 1024 * time_diff
            self.wifi_sent = cur_sent
            self.wifi_receive = cur_recv
            self.time_temp = _time
        else:
            sent_ps = 'NaN'
            resc_ps = 'NaN'
        wifi_stat = [sent_ps, resc_ps]

        return init_info + temperature + processes_cpu + others + wifi_stat

    def make_table(self) -> None:
        """テーブルを作成"""
        self.tree = ttk.Treeview(self.master, height=13, columns=(1,2))

        self.tree.column('#0', width=self.width//2-20)
        self.tree.column(1, width=self.width//2-50)
        self.tree.column(2, width=50)

        self.tree.heading('#0', text='Name')
        self.tree.heading(1, text="Value")
        self.tree.heading(2, text="Unit")

        self.id_list = []

        processes = self.get_status()

        master_usage_id = ''
        master_power_id = ''
        master_clock_id = ''
        master_temp_id = ''

        for index, (name, proc, fmt) in enumerate(zip(self.name, processes, self.unit)):
            if name in self._cpu_usage[1:]:
                id = self.tree.insert(
                    master_usage_id, "end", tags=index, text=name, values=(self.conv_proc_fmt(proc), fmt))
            elif name in self._cpu_power[1:]:
                id = self.tree.insert(
                    master_power_id, "end", tags=index, text=name, values=(self.conv_proc_fmt(proc), fmt))
            elif name in self._cpu_freq[1:]:
                id = self.tree.insert(
                    master_clock_id, "end", tags=index, text=name, values=(self.conv_proc_fmt(proc), fmt))
            elif len(self._cpu_temp) > 1 and name in self._cpu_temp[1:]:
                id = self.tree.insert(
                    master_temp_id, "end", tags=index, text=name, values=(self.conv_proc_fmt(proc), fmt))
            else:
                id = self.tree.insert("", "end", tags=index, text=name, values=(self.conv_proc_fmt(proc), fmt))
                if name == 'CPU usage':
                    master_usage_id = id
                elif name == 'CPU power':
                    master_power_id = id
                elif name == 'CPU bus':
                    master_clock_id = id
                elif name == 'Battery':
                    self.battery_id = id
                elif name == 'Temperature':
                    master_temp_id = id
            self.set_color(index, name, proc)
            self.id_list.append(id)
        self.tree.pack()

    def conv_proc_fmt(self, proc) -> str:
        """フォーマットを整理"""
        if isinstance(proc, float):
            proc_str = f'{proc:.1f}'
        else:
            proc_str = str(proc)
        return proc_str
    
    def _clip(self, value, round_float = True, color_max = None):
        value = round(value) if round_float else value
        color_max = color_max or self.COLOR_MAX
        if value < 0:
            return 0
        return color_max if value > color_max else value
    
    def _color_code(self, r, g, b):
        return '#{:0>2X}{:>02X}{:>02X}'.format(r, g, b)

    def set_color(self, tag, name, proc) -> None:
        """テーブルのフォントの色を値に応じて変化させる"""
        if isinstance(proc, float) and not name in self.exclude:
            proc = self._clip(proc, False, 100.)
            value = (-proc/100.)**3 if name in ['Disk usage', 'Memory'] else - proc/100.
            p = self._clip(self.COLOR_MAX*(value + 1))
            cl = self._color_code(self.COLOR_MAX, p, p)
        elif name == 'Battery' and proc != -1:
            p = round(self.COLOR_MAX * self._clip(proc, False, 100.) / 100.)
            rc = self.COLOR_MAX if p < 0x80 else self._clip((-0x83*p + 0xc001)/0x7f)
            gc = 2*p if p < 0x80 else self._clip((-0x03*p + 0x8001)/0x7f)
            cl = self._color_code(rc, gc, 0)
        elif name == 'AC status' and proc != 'Unknown':
            if proc == 'Offline':
                cl = '#ffff00'
            elif proc == 'Online':
                cl = '#7cfc00'
        elif (name == 'Battery status' and proc in self.bcs_name_fix):
            if proc in ['High', 'Charging', 'Charging(High)']:
                cl = '#7cfc00'
            elif proc in ['Low', 'Charging(Low)', 'Charging(Critical)']:
                cl = '#ffff00'
            elif proc == 'Critical':
                cl = '#ff0000'
        elif name == 'GPU power':
            if isinstance(self.MAX_GPU_POWER, (int, float)) and self.MAX_GPU_POWER > 0:
                p = self._clip(self.COLOR_MAX * (1. - proc / self.MAX_GPU_POWER))
                cl = self._color_code(self.COLOR_MAX, p, p)
        
        try: cl
        except:
            cl = 'white'

        self.tree.tag_configure(tagname=tag, foreground=cl)

    def check_moveable(self):
        if self.w_bind and self.h_bind:
            return

        move = False

        # ウィンドウサイズが変わったとき
        wsize, hsize = cs_ops.workingarea()

        if not self.w_bind and wsize != self.window_width:
            self.window_width = wsize
            move = True

        if not self.h_bind and hsize != self.window_height:
            self.window_height = hsize
            move = True

        if move:
            self.set_position()     

    def update(self) -> None:
        """更新時の挙動"""
        self.check_moveable()

        # 次状態を取得
        processes = self.get_status()
        for i, (index, proc) in enumerate(zip(self.id_list, processes)):
            self.tree.set(index, 1, value=self.conv_proc_fmt(proc))
            self.set_color(i, self.name[i], proc)

            # バッテリー残量のお知らせ
            if self.battery_id == index and self.use_battery:
                current = processes[1]
                charging = processes[0] == cs_ops.PowerLineStatus.Online

                if current <= self.BATTERY_ALERT_MIN and not charging and not self.battery_warn:
                    # 残量がないとき
                    show_notification(
                        message = f'残りバッテリ―容量が{self.BATTERY_ALERT_MIN}%です。ACアダプタを接続してください。')
                    self.battery_warn = True
                elif current >= self.BATTERY_ALERT_MAX and charging and not self.battery_full:
                    # 十分充電されたとき
                    show_notification(
                        message = 'PCは十分に充電されています。')
                    self.battery_full = True
                elif current > self.BATTERY_ALERT_MIN and current < self.BATTERY_ALERT_MAX:
                    # 特にないとき
                    self.battery_full = False
                    self.battery_warn = False
        self.master.after(self.cycle, self.update)

    def app_exit(self, *args, **kwargs) -> None:
        """プログラム終了"""
        print('App exit.')
        self.master.destroy()

    def dump_current_status(self, *args, **kwargs) -> None:
        """
        各情報をjson形式で出力(full output)
        """
        currents = self.ohm.curstatus()
        print(currents, flush=True)
        _date = datetime.datetime.now().strftime('%Y_%m_%d')
        fpath = os.path.join(TASKMGR_PATH, _date+'_dump.json')
        add_summary = dict(recorded = _date)
        if self.use_battery:
            add_summary['Battery Status (all)'] = cs_ops.get_battery_status().tolist()
        try:
            with open(fpath, 'w') as f:
                summary = dict(**currents.todict(), **add_summary)
                json.dump(summary, f, indent=4)
        except PermissionError:
            show_notification('保存に失敗しました。アクセスが拒否されました。')
        else:
            show_notification(f'ダンプファイルを{fpath}に保存しました。')

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
            'Ctrl + B ... 情報の更新速度を0.5s間隔に変更 / 1s間隔に戻す\n\n'
            '※ ノートPCにおいて起動時から電源プラグが刺さった状態の場合、\n'
            '　 一度プラグ抜くとこのアプリが強制終了する場合があります。')

        print(msg)
        cs_ops.info(msg)


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
        self.window_height = cs_ops.workingarea()[1]
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
        self.window_width = cs_ops.workingarea()[0]
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

def runapp(ohm: OpenHardWareMonitor):
    window = tk.Tk()
    MainWindow(window, 340, 272, ohm)
    window.mainloop()

def main() -> None:
    error_catch = 0
    msg = None

    dllpath = os.path.join(TASKMGR_PATH,'OpenHardwareMonitorLib')
    ohm = OpenHardWareMonitor(dllpath)
    try:
        runapp(ohm)
    except (Exception, KeyboardInterrupt) as e:
        msg = repr(e)
        error_catch = 1
    ohm.close()

    if msg:
        msg_box = cs_ops.error if not __debug__ else show_notification
        msg_box(msg)
    cs_ops.close_container()
    sys.exit(error_catch)

if __name__ == '__main__':
    try:
        import subprocess
        subprocess.check_output(['net', 'session'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError: # status != 0
        cs_ops.error('管理者権限を有効にして実行してください。')
    else:
        main()
