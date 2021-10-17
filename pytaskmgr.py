"""PyTaskManager"""
import re
import ctypes
import datetime
import json
import os
import sys
import tkinter as tk
import tkinter.ttk as ttk
from ctypes.wintypes import BOOL, BYTE, DWORD
from typing import Dict, List, Union, Optional

import clr
import psutil
import ttkthemes

DEBUG_MODE = not __debug__
PYTASKMGR = 'PyTaskManager'
TASKMGR_PATH = os.path.split(os.path.abspath(__file__))[0]
ICON = os.path.join(TASKMGR_PATH, 'shared.ico')
TCL_PATH = os.path.join(TASKMGR_PATH, 'azure.tcl')

if DEBUG_MODE:
    PYTASKMGR += ' (Debug Mode)'

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.ComponentModel.Primitives')
clr.AddReference('System.Drawing')
clr.AddReference(os.path.join(TASKMGR_PATH,'OpenHardwareMonitorLib'))
import System.Windows.Forms as forms # type: ignore
from System.ComponentModel import Container # type: ignore
from System.Drawing import Icon, SystemIcons # type: ignore
from OpenHardwareMonitor import Hardware # type: ignore


# タスクバーの高さを除く画面サイズ
WOTB_WIDTH = forms.Screen.PrimaryScreen.WorkingArea.Width
WOTB_HEIGHT = forms.Screen.PrimaryScreen.WorkingArea.Height


def show_notification(
    message: str = '',
    title: Optional[str] = None,
    app_icon: Optional[str] = None):

    app_icon = app_icon or ICON
    if os.path.exists(app_icon):
        icon = Icon(app_icon)
    else:
        icon = SystemIcons.Application

    notifyicon = forms.NotifyIcon(Container())
    notifyicon.Icon = icon
    notifyicon.BalloonTipTitle = title or PYTASKMGR
    notifyicon.BalloonTipText = message
    notifyicon.Visible = True
    notifyicon.ShowBalloonTip(1)

# Network
WIFI_KEY = None

# ネットワーク(Byte)
def get_wifi_usage():
    global WIFI_KEY
    net_status = psutil.net_io_counters(pernic=True, nowrap=True)
    if not WIFI_KEY:
        key_found = False
        try:
            net_status['Wi-Fi']
        except KeyError:
            for k in net_status.keys():
                if re.match('Wi-Fi', k):
                    WIFI_KEY = k
                    key_found = True
                    break
            if not key_found: WIFI_KEY = -1
        else:
            WIFI_KEY = 'Wi-Fi'
            key_found = True
    
    if not isinstance(WIFI_KEY, int):
        net_status = net_status[WIFI_KEY]
        bytes_sent = net_status.bytes_sent
        bytes_recv = net_status.bytes_recv
        return bytes_sent, bytes_recv
    return None, None
WIFI_SENT, WIFI_RECV = get_wifi_usage()


class OpenHardWareMonitor(object):
    """
    OpenHardWareMonitorからの情報を取得する

    参考
    https://stackoverflow.com/questions/3262603/accessing-cpu-temperature-in-python

    https://github.com/openhardwaremonitor/openhardwaremonitor/tree/master/Hardware
    """
    _hwtypes: List[str] = [
        'Mainboard','SuperIO',
        'CPU','RAM',
        'GpuNvidia','GpuAti',
        'TBalancer','Heatmaster','HDD']
    _sensortypes: List[str] = [
        'Voltage','Clock',
        'Temperature','Load',
        'Fan','Flow',
        'Control','Level',
        'Factor','Power',
        'Data','SmallData',
        'Throughput']
    _sensortypeformat: List[str] = [
        'V','MHz','deg','%',
        'RPM','L/h','%','%',
        '','W','GB','GB','MB/s'
    ]
    _sensor_dict: Dict[str, str] = dict(zip(_sensortypes, _sensortypeformat))

    def __init__(self) -> None:
        self.handle = None
        self.status = {}
        self.load_ohm()
        self._closed = False

    def load_ohm(self) -> None:
        if self.handle is not None:
            return
        self.handle = Hardware.Computer()
        self.handle.CPUEnabled = True
        self.handle.RAMEnabled = True
        self.handle.GPUEnabled = True
        self.handle.HDDEnabled = True
        self.handle.Open()

    def curstatus(self, full: bool=False)-> Dict[str, dict]:
        self.status = {}
        for i in self.handle.Hardware:
            i.Update()
            for sensor in i.Sensors:
                self.parse_sensor(sensor, full)
            for j in i.SubHardware:
                j.Update()
                for subsensor in j.Sensors:
                    self.parse_sensor(subsensor, full)
        return self.status

    def parse_sensor(self, sensor, full: bool) -> None:
        key = self._hwtypes[sensor.Hardware.HardwareType]
        _stype = sensor.SensorType
        if _stype not in self._sensortypes:
            stype = str(sensor.Identifier).split('/')[-2].capitalize()
            self._sensor_dict.update({stype: ''})
        else:
            stype = self._sensortypes[_stype]
        if key not in self.status:
            self.status[key] = dict()
        if full:
            name = sensor.Hardware.Name
            if name not in self.status[key].keys():
                self.status[key][name] = {}
            if stype not in self.status[key][name].keys():
                self.status[key][name][stype] = {}
            self.status[key][name][stype][sensor.Index] = {
                'Identifier': str(sensor.Identifier),
                'Value': sensor.Value,
                'Min': sensor.Min,
                'Max': sensor.Max,
                'Format': self._sensor_dict[stype]}
        else:
            if stype not in self.status[key].keys():
                self.status[key][stype] = dict()
            self.status[key][stype][sensor.Index] = sensor.Value

    def close(self) -> None:
        if self._closed:
            print('OpenHardwareMoniter is already closed.')
            return
        self.handle.Close()
        self._closed = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args, **kwargs):
        if not self._closed:
            self.close()

    @property
    def has_nvidia_gpu(self):
        return 'GpuNvidia' in self.curstatus()

    def get_cpu_sizes(self, key: str) -> int:
        status = self.curstatus()['CPU']
        ret = {}
        for st in status:
            ret[st] = len(status[st])
        if key in ret:
            return ret[key]

        # 見つからないとき
        self.close()
        forms.MessageBox.Show(
            f'OpenHardWareMonitor: {key}が見つかりませんでした。', PYTASKMGR,
            forms.MessageBoxButtons.OK, forms.MessageBoxIcon.Error)
        sys.exit(1)


class SYSTEM_POWER_STATUS(ctypes.Structure):
    """
    https://docs.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-system_power_status
    """
    _fields_ = [
        ('ACLineStatus', BYTE),
        ('BatteryFlag', BYTE),
        ('BatteryLifePercent', BYTE),
        ('Reserved1', BYTE),
        ('BatteryLifeTime', DWORD),
        ('BatteryFullLifeTime', DWORD),
    ]


class MainWindow(ttk.Frame):
    _AC_STATUS: Dict[str, str] = {0: 'Offline',1: 'Online',255: 'Unknown'}
    _BATTERY_FLAG: Dict[str, str] = {
        0: 'Uncharged',
        1: 'High',
        2: 'Low',
        4: 'Critical',
        8: 'Charging',
        9: 'Charging(High)',
        10: 'Charging(Low)',
        12: 'Charging(Critical)',
        128: 'Undefined'
    }
    COLOR_MAX = 255
    BATTERY_ALERT_MIN: int = 35
    BATTERY_ALERT_MAX: int = 95
    MAX_GPU_POWER = None

    def get_name(self) -> str:
        if not self.use_battery:
            self._init_name = ['GPU fan', 'GPU power', 'GPU temperature']
            self.type = 'gpu'
        else:
            self._init_name = ['AC status','Battery', 'Battery status']
            self.type = 'ac'

        self._cpu_usage: List[str] = ['CPU usage']+\
            [f'CPU #{i+1} usage' for i in range(psutil.cpu_count())]
        self._cpu_freq: List[str] = ['CPU bus'] +\
            [f'CPU #{i+1} clock' for i in range(self.ohm.get_cpu_sizes('Clock')-1)]
        self._cpu_power: List[str] = ['CPU power', 'CPU (cores) power'] +\
            [f'CPU #{i+1} power' for i in range(self.ohm.get_cpu_sizes('Power')-2)]
        
        cpus = ['CPU temperature'] + self._cpu_usage + self._cpu_freq + self._cpu_power

        self._system = [
            'Disk usage', 'Memory',
            'Running PIDs',
            'WiFi usage (In)',
            'WiFi usage (Out)'
            ]

        self.exclude = self._cpu_freq + self._cpu_power +\
            ['WiFi usage (In)', 'WiFi usage (Out)'] + ['GPU fan', 'GPU power']
        return self._init_name + cpus + self._system

    def __init__(self, master: tk.Tk=None, width: int=640, height: int=480, ohm: OpenHardWareMonitor=None) -> None:
        super().__init__(master)
        self.master = master
        self.pack()

        if os.path.exists(TCL_PATH):
            self.master.tk.call("source", TCL_PATH)
            self.master.tk.call("set_theme", "dark")
        else:
            #show_notification(message='TCL file not found. Using ttkthemes...')
            style = ttkthemes.ThemedStyle(
                master=self.master,
                theme='black')
            style.map(
                    'Treeview',
                    foreground=[
                        Elm for Elm in style.map("Treeview", query_opt='foreground') if Elm[:2] != ("!disabled", "!selected")])
            
        self.ohm = ohm

        self.battery_id = ''
        self.battery_full = False        
        self.battery_warn = False
        self.cls_name = self.__class__.__name__
        self.cycle = 1000
        if self.ohm.has_nvidia_gpu and psutil.sensors_battery() is not None:
            result = forms.MessageBox.Show(
                'Nvidia GPUを検出しました。バッテリ―状態の代わりに表示しますか?', PYTASKMGR,
                forms.MessageBoxButtons.YesNo, forms.MessageBoxIcon.Exclamation)
            self.use_battery = result == forms.DialogResult.Yes
        else:
            self.use_battery = psutil.sensors_battery() is not None
        self.name = self.get_name()
        self.height = height
        self.width = width
        self.h_bind = False
        self.w_bind = False
        self.showtop = True
        self.transparent = False
  
        # masterの設定
        self.hide_titlebar = False
        self.set_position()
        # self.master.overrideredirect(True)
        if ICON is not None and os.path.exists(ICON):
            self.master.iconbitmap(ICON)
        self.master.bind('<Control-Key-q>', self.app_exit)
        self.master.bind('<Control-Key-p>', self.switch_topmost)
        self.master.bind('<Control-Key-s>', self.dump_current_status)
        self.master.bind('<Control-Key-k>', self.move_u)
        self.master.bind('<Control-Key-m>', self.move_d)
        self.master.bind('<Control-Key-j>', self.move_l)
        self.master.bind('<Control-Key-l>', self.move_r)
        self.master.bind('<Control-Key-r>', self.switch_window_transparency)
        self.master.bind('<Control-Key-b>', self.switch_cycle)
        self.master.title('Process')
        self.master.attributes("-topmost", self.showtop)
        self.master.resizable(width=False, height=False)

        if not DEBUG_MODE:
            self.move_u()

        # 表示する単位の設定
        self.set_format()

        # テーブル作成
        self.make_table()

        # 更新用の関数
        self.update()

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
        pos_w = WOTB_WIDTH - self.width
        pos_h = WOTB_HEIGHT - self.height
        if not self.hide_titlebar:
            frame_border = forms.SystemInformation.FrameBorderSize
            border = forms.SystemInformation.BorderSize
            if not self.w_bind:
                pos_w -= (frame_border.Width + border.Width)
            if not self.h_bind:
                pos_h -= (frame_border.Height + border.Height)
        self.master.geometry(f'{self.width}x{self.height}+{pos_w}+{pos_h}')

    def get_battery_status(self) -> Dict[str, int]:
        """
        バッテリー状態の取得
        https://github.com/kivy/plyer/tree/master/plyer/platforms/win/libs
        """
        status = SYSTEM_POWER_STATUS()
        GetSystemPowerStatus = ctypes.windll.kernel32.GetSystemPowerStatus
        GetSystemPowerStatus.argtypes = [ctypes.POINTER(SYSTEM_POWER_STATUS)]
        GetSystemPowerStatus.restype = BOOL
        GetSystemPowerStatus(ctypes.pointer(status))
        ret = {}
        for field, _ in status._fields_:
            if field == 'BatteryFlag':
                st = getattr(status, field)
                if st < 0 or (st & 8 ==0 and st & 128 != 0):
                    field_set = 128
                else:
                    field_set = st
                ret[field] = field_set
            else:
                ret[field] = getattr(status, field)
        return ret

    def get_status(self) -> List[Union[str, int]]:
        """
        各情報を取得する
        """
        global WIFI_SENT, WIFI_RECV

        # OHMからの情報
        self.ohm_status = self.ohm.curstatus()

        if self.type == 'ac':
            # バッテリー情報
            ac_info = self.get_battery_status()
            init_info= [
                self._AC_STATUS[ac_info['ACLineStatus']],
                int(psutil.sensors_battery().percent) if self.use_battery else -1,
                self._BATTERY_FLAG[ac_info['BatteryFlag']],
            ]
        elif self.type == 'gpu':
            # gpu
            gpu_info = self.ohm_status['GpuNvidia']
            init_info = [
                gpu_info['Fan'][0],
                gpu_info['Power'][0],
                gpu_info['Temperature'][0]
            ]

        # CPU温度
        self.ohm_status = self.ohm_status['CPU']
        try:
            temperature = [self.ohm_status['Temperature'][0]]
        except KeyError:
            # 無ければ
            temperature = ['NaN']

        # cpu使用率
        processes_cpu = [psutil.cpu_percent()] + psutil.cpu_percent(percpu=True)

        self.master.title('CPU: {:>5}%, Temp: {:>4.1f}°C'.format(processes_cpu[0], temperature[0]))

        # クロック周波数
        try:
            processes_cpu += [p for p in self.ohm_status['Clock'].values()]
        except KeyError:
            processes_cpu += ['NaN']

        # 電力
        try:
            processes_cpu += [p for p in self.ohm_status['Power'].values()]
        except KeyError:
            processes_cpu += ['NaN']

        # その他
        others = [
            psutil.disk_usage('/').percent,         # Cドライブ使用量
            psutil.virtual_memory().percent,        # RAM使用量 
            len(psutil.pids()),                     # PID数
        ]

        # Wifi使用量(MB/s)、単位修正含む
        if not isinstance(WIFI_KEY, int):
            cur_sent, cur_recv = get_wifi_usage()
            sent_ps = (cur_sent - WIFI_SENT) / 0x400 * (self.cycle/1000)
            resc_ps = (cur_recv - WIFI_RECV) / 0x400 * (self.cycle/1000)
            WIFI_SENT = cur_sent
            WIFI_RECV = cur_recv
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
            if name in ['Disk usage', 'Memory']:
                value = 1. + (-proc/100.)**3
            else:
                value = 1. - proc/100.
            p = self._clip(self.COLOR_MAX*value)
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
        elif name == 'Battery status' and proc in self._BATTERY_FLAG.values():
            if proc in ['High', 'Charging', 'Charging(High)']:
                cl = '#7cfc00'
            elif proc in ['Low', 'Charging(Low)', 'Charging(Critical)']:
                cl = '#ffff00'
            elif proc == 'Critical':
                cl = '#ff0000'
            else:
                cl = 'white'
        elif name == 'GPU power':
            if isinstance(self.MAX_GPU_POWER, (int, float)) and self.MAX_GPU_POWER > 0:
                p = self._clip(self.COLOR_MAX * (1. - proc / self.MAX_GPU_POWER))
                cl = self._color_code(self.COLOR_MAX, p, p)
            else:
                cl = 'white'
        else:
            cl = 'white'
        
        self.tree.tag_configure(tagname=tag, foreground=cl)

    def check_moveable(self):
        global WOTB_HEIGHT, WOTB_WIDTH

        if self.w_bind and self.h_bind:
            return

        move = False

        # ウィンドウサイズが変わったとき
        wsize = forms.Screen.PrimaryScreen.WorkingArea.Width
        hsize = forms.Screen.PrimaryScreen.WorkingArea.Height
        
        if not self.w_bind and wsize != WOTB_WIDTH:
            WOTB_WIDTH = wsize
            move = True

        if not self.h_bind and hsize != WOTB_HEIGHT:
            WOTB_HEIGHT = hsize
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
                current = psutil.sensors_battery().percent
                charging = True if self.get_battery_status()['ACLineStatus'] == 1 else False

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
        self.master.destroy()

    def dump_current_status(self, *args, **kwargs) -> None:
        """
        各情報をjson形式で出力(full output)
        """
        summary_1 = dict(zip(self.name, self.get_status()))
        summary_2 = {}
        if self.use_battery:
            summary_2['Battery Status (all)'] = self.get_battery_status()
        summary_2['WMI Status (all)'] = self.ohm.curstatus(full=True)

        _date = datetime.datetime.now()
        fpath = os.path.join(TASKMGR_PATH, _date.strftime('%Y_%m_%d')+'_dump.json')
        try:
            with open(fpath, 'w') as f:
                summary = dict(**summary_1, **summary_2)
                json.dump(summary, f, indent=4)
        except PermissionError:
            show_notification(
                message='保存に失敗しました。アクセスが拒否されました。'
            )
        else:
            show_notification(
                message=f'ダンプファイルを{fpath}に保存しました。')

    def move_u(self, *args, **kwargs) -> None:
        """上へ"""
        if self.h_bind:
            return
        global WOTB_HEIGHT
        WOTB_HEIGHT = self.height
        self.h_bind = True
        self.set_position()

    def move_d(self, *args, **kwargs) -> None:
        """下へ"""
        if not self.h_bind:
            return
        global WOTB_HEIGHT
        WOTB_HEIGHT = forms.Screen.PrimaryScreen.WorkingArea.Height
        self.h_bind = False
        self.set_position()

    def move_l(self, *args, **kwargs) -> None:
        """左へ"""
        if self.w_bind:
            return
        global WOTB_WIDTH
        WOTB_WIDTH = self.width
        self.w_bind = True
        self.set_position()

    def move_r(self, *args, **kwargs) -> None:
        """右へ"""
        if not self.w_bind:
            return
        global WOTB_WIDTH
        WOTB_WIDTH = forms.Screen.PrimaryScreen.WorkingArea.Width
        self.w_bind = False
        self.set_position()

    def switch_topmost(self, *args, **kwargs) -> None:
        """ウィンドウ最前面固定の有効/無効"""
        self.showtop = not self.showtop
        self.master.attributes("-topmost", self.showtop)

    def switch_window_transparency(self, *args, **kwargs):
        if self.transparent:
            alpha = 1.0
        else:
            alpha = 0.5
        self.transparent = not self.transparent
        self.master.attributes("-alpha",alpha)

    def switch_cycle(self, *args, **kwargs):
        if self.cycle == 1000:
            self.cycle = 500
        else:
            self.cycle = 1000

def runapp(ohm: OpenHardWareMonitor):
    window = tk.Tk()
    MainWindow(window, 340, 272, ohm)
    window.mainloop()

def main() -> None:
    error_catch = 0
    with OpenHardWareMonitor() as ohm:
        try:
            runapp(ohm)
        except (Exception, KeyboardInterrupt) as e:
            msg = repr(e)
            if DEBUG_MODE:
                forms.MessageBox.Show(
                    msg, PYTASKMGR,
                    forms.MessageBoxButtons.OK, forms.MessageBoxIcon.Error)
            else:
                show_notification(message = msg)
            error_catch = 1
    sys.exit(error_catch)

if __name__ == '__main__':
    try:
        import subprocess
        subprocess.check_output(['net', 'session'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError: # status != 0
        forms.MessageBox.Show(
            '管理者権限を有効にして実行してください。', PYTASKMGR,
            forms.MessageBoxButtons.OK, forms.MessageBoxIcon.Error)
        sys.exit(1)
    else:
        main()
