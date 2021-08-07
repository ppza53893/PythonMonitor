"""PyTaskManager"""
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
import plyer
import psutil
import ttkthemes

TASKMGR_PATH = os.path.split(os.path.abspath(__file__))[0]
ICON = None

clr.AddReference('System.Windows.Forms')
clr.AddReference(os.path.join(TASKMGR_PATH,'OpenHardwareMonitorLib'))
from System.Windows.Forms import Screen # type: ignore
from OpenHardwareMonitor import Hardware # type: ignore


# タスクバーの高さを除く画面サイズ
WOTB_WIDTH = Screen.PrimaryScreen.WorkingArea.Width
WOTB_HEIGHT = Screen.PrimaryScreen.WorkingArea.Height


# ネットワーク(Byte)
def get_wifi_usage():
    net_status = psutil.net_io_counters(pernic=True, nowrap=True)['Wi-Fi']
    bytes_sent = net_status.bytes_sent
    bytes_recv = net_status.bytes_recv
    return bytes_sent, bytes_recv
WIFI_SENT, WIFI_RECV = get_wifi_usage()


def show_notification(
    title: str,
    message: str,
    app_name: str = 'PyTaskManager',
    app_icon: Optional[str] = ICON,
    timeout: int = 10,
    **kwargs):
    """Windowsの通知を出す"""

    if app_icon is None or not os.path.exists(app_icon):
        app_icon = ''

    plyer.notification.notify(
        title = title,
        message = message,
        app_name = app_name,
        app_icon = app_icon,
        timeout = timeout,
        **kwargs
    )


class _OpenHardWareMonitor(object):
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
        try:
            stype = self._sensortypes[sensor.SensorType]
        except KeyError:
            stype = str(sensor.Identifier).split('/')[-2].capitalize()
            self._sensor_dict = dict(
                **self._sensor_dict,
                **{stype: ''}
            )
        if key not in self.status.keys():
            self.status[key] = {}
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
                self.status[key][stype] = {}
            self.status[key][stype][sensor.Index] = sensor.Value

    def close(self) -> None:
        self.handle.Close()

    def get_cpu_sizes(self, key: str) -> int:
        status = self.curstatus()['CPU']
        ret = {}
        for st in status:
            ret[st] = len(status[st])
        if key in ret:
            return ret[key]

        # 見つからないとき。管理者権限でないとエラーが出る
        self.close()
        show_notification(
            title='エラー',
            message=f'OpenHardWareMonitor: {key}が見つかりませんでした。\n'
            'もし管理者権限モードで実行していなければ、権限モードでこのプログラムを再実行してください。',
            timeout=8)
        sys.exit(1)
OpenHardWareMonitor = _OpenHardWareMonitor()


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


class MainWindow(tk.Frame):
    _CPU_STATUS_NAME: List[str] = ['CPU usage']+\
        [f'CPU #{i+1} usage' for i in range(psutil.cpu_count())]
    _CPU_STATUS_NAME_C: List[str] = ['CPU bus'] +\
        [f'CPU #{i+1} clock' for i in range(OpenHardWareMonitor.get_cpu_sizes('Clock')-1)]
    _CPU_STATUS_NAME_W: List[str] = ['CPU power', 'CPU (cores) power'] +\
        [f'CPU #{i+1} power' for i in range(OpenHardWareMonitor.get_cpu_sizes('Power')-2)]
    _NAME: List[str] = [
        'AC status','Battery',
        'Battery status','CPU temperature'
        ]+\
            _CPU_STATUS_NAME+_CPU_STATUS_NAME_C+_CPU_STATUS_NAME_W+\
        [
        'Disk usage', 'Memory',
        'Running PIDs',
        'WiFi usage (In)',
        'WiFi usage (Out)'
        ]
    _AC_STATUS: Dict[str, str] = {0: 'Offline',1: 'Online',255: 'Unknown'}
    _BATTERY_FLAG: Dict[str, str] = {
        0: 'Uncharged',
        1: 'High',
        2: 'Low',
        4: 'Critical',
        8: 'Charging',
        9: 'Charging(High)',
        10: 'Chargin(Low)',
        12: 'Charging(Critical)',
        128: 'Undefined'
    }
    BATTERY_ALERT_MIN: int = 35
    BATTERY_ALERT_MAX: int = 95

    def __init__(self, master: tk.Tk=None, width: int=640, height: int=480) -> None:
        super().__init__(master)
        self.master = master
        self.pack()

        self.battery_id = ''
        self.battery_full = False        
        self.battery_warn = False
        self.cls_name = self.__class__.__name__
        self.cycle = 1000
        self.has_battery = psutil.sensors_battery() is not None
        self.height = height
        self.width = width
        self.h_bind = False
        self.w_bind = False
        self.showtop = True
        self.transparent = False
  
        # masterの設定
        self.set_position()
        self.master.overrideredirect(True)
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

        # 表示する単位の設定
        self.set_format()

        # テーブル作成
        self.make_table()

        # 更新用の関数
        self.update()

    def set_format(self) -> None:
        self._FMT = []
        for name in self._NAME:
            if name in ['Running PIDs', 'AC status', 'Battery status']:
                self._FMT.append('')
            elif name in ['WiFi usage (In)', 'WiFi usage (Out)']:
                self._FMT.append('KB/s')
            elif name == 'CPU temperature':
                self._FMT.append('°C')
            elif name in self._CPU_STATUS_NAME_W:
                self._FMT.append('W')
            elif name in self._CPU_STATUS_NAME_C:
                self._FMT.append('MHz')
            else:
                self._FMT.append('%')

    def set_position(self) -> None:
        """位置をセットする"""
        pos_w = WOTB_WIDTH - self.width
        pos_h = WOTB_HEIGHT - self.height
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

        # バッテリー情報
        bres = self.get_battery_status()
        battery_info = [
            self._AC_STATUS[bres['ACLineStatus']],
            int(psutil.sensors_battery().percent) if self.has_battery else -1,
            self._BATTERY_FLAG[bres['BatteryFlag']],
        ]

        # OHMからの情報
        self.ohm_status = OpenHardWareMonitor.curstatus()['CPU']

        # CPU温度
        try:
            temperature = [self.ohm_status['Temperature'][0]]
        except KeyError:
            # 無ければ-1
            temperature = [-1.]

        # cpu使用率
        processes_cpu = [psutil.cpu_percent()] + psutil.cpu_percent(percpu=True)

        # クロック周波数
        processes_cpu += [p for p in self.ohm_status['Clock'].values()]

        # 電力
        processes_cpu += [p for p in self.ohm_status['Power'].values()]

        # その他
        others = [
            psutil.disk_usage('/').percent,         # Cドライブ使用量
            psutil.virtual_memory().percent,        # RAM使用量 
            len(psutil.pids()),                     # PID数
        ]

        # Wifi使用量(MB/s)、単位修正含む
        cur_sent, cur_recv = get_wifi_usage()
        sent_ps = (cur_sent - WIFI_SENT) / 0x400 * (self.cycle/1000)
        resc_ps = (cur_recv - WIFI_RECV) / 0x400 * (self.cycle/1000)
        WIFI_SENT = cur_sent
        WIFI_RECV = cur_recv
        wifi_stat = [sent_ps, resc_ps]

        return battery_info + temperature + processes_cpu + others + wifi_stat

    def make_table(self) -> None:
        """テーブルを作成"""
        self.tree = ttk.Treeview(self.master, height=13, columns=(1,2))

        self.tree.column('#0', width=self.width//2-20)
        self.tree.column(1, width=self.width//2-20)
        self.tree.column(2, width=40)

        self.tree.heading('#0', text='Name')
        self.tree.heading(1, text="Value")
        self.tree.heading(2, text="Unit")

        self.id_list = []

        processes = self.get_status()

        master_usage_id = ''
        master_power_id = ''
        master_clock_id = ''

        for index, (name, proc, fmt) in enumerate(zip(self._NAME, processes, self._FMT)):
            if name in self._CPU_STATUS_NAME[1:]:
                id = self.tree.insert(
                    master_usage_id, "end", tags=index, text=name, values=(self.conv_proc_fmt(proc), fmt))
            elif name in self._CPU_STATUS_NAME_W[1:]:
                id = self.tree.insert(
                    master_power_id, "end", tags=index, text=name, values=(self.conv_proc_fmt(proc), fmt))
            elif name in self._CPU_STATUS_NAME_C[1:]:
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

    def set_color(self, tag, name, proc) -> None:
        """テーブルのフォントの色を値に応じて変化させる"""
        color_max = 0xff
        exclude = self._CPU_STATUS_NAME_C + self._CPU_STATUS_NAME_W + ['WiFi usage (In)', 'WiFi usage (Out)']
        if isinstance(proc, float) and not name in exclude:
            if proc > 100.:
                proc = 100.
            percent = 1.-proc/100.
            p = round(color_max * percent)
            cl = '#{:0>2X}{:>02X}{:>02X}'.format(color_max, p, p)
        elif name == 'Battery' and proc != -1:
            threth_check = lambda x: color_max if x > color_max else x
            if proc > 100:
                proc = 100
            percent = proc/100.
            p = round(color_max * percent)
            rc = color_max if p < 0x80 else threth_check(round((-0x83*p + 0xc001)/0x7f))
            gc = threth_check(round((-0x03*p + 0x8001)/0x7f) if p > 0x80 else 2*p)
            cl = '#{:0>2X}{:>02X}{:>02X}'.format(rc, gc, 0)
        elif name == 'AC status' and proc != 'Unknown':
            if proc == 'Offline':
                cl = '#ffff00'
            elif proc == 'Online':
                cl = '#7cfc00'
        elif name == 'Battery status' and proc in [
            'High', 'Low', 'Critical',
            'Charging', 'Charging(High)', 'Charging(Low)', 'Charging(Critical)']:
            if proc in ['High', 'Charging', 'Charging(High)']:
                cl = '#7cfc00'
            elif proc in ['Low', 'Charging(Low)']:
                cl = '#ffff00'
            elif proc in ['Critical', 'Charging(Critical)']:
                cl = '#ff0000'
        else:
            cl = 'white'
        self.tree.tag_configure(tagname=tag, foreground=cl)

    def check_moveable(self):
        global WOTB_HEIGHT, WOTB_WIDTH

        if self.w_bind and self.h_bind:
            return

        move = False

        # ウィンドウサイズが変わったとき
        wsize = Screen.PrimaryScreen.WorkingArea.Width
        hsize = Screen.PrimaryScreen.WorkingArea.Height
        
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
            self.set_color(i, self._NAME[i], proc)

            # バッテリー残量のお知らせ
            if self.battery_id == index and self.has_battery:
                current = psutil.sensors_battery().percent
                charging = True if self.get_battery_status()['ACLineStatus'] == 1 else False

                if current <= self.BATTERY_ALERT_MIN and not charging and not self.battery_warn:
                    # 残量がないとき
                    show_notification(
                        title = 'バッテリー残量の警告',
                        message = f'残りバッテリ―容量が{self.BATTERY_ALERT_MIN}%です。ACアダプタを接続してください。')
                    self.battery_warn = True
                elif current >= self.BATTERY_ALERT_MAX and charging and not self.battery_full:
                    # 十分充電されたとき
                    show_notification(
                        title = 'バッテリー充電',
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
        summary_1 = dict(zip(self._NAME, self.get_status()))
        summary_2 = {}
        summary_2['Battery Status (all)'] = self.get_battery_status()
        summary_2['WMI Status (all)'] = OpenHardWareMonitor.curstatus(full=True)

        _date = datetime.datetime.now()
        fpath = os.path.join(TASKMGR_PATH, _date.strftime('%Y_%m_%d')+'_dump.json')
        try:
            with open(fpath, 'w') as f:
                summary = dict(**summary_1, **summary_2)
                json.dump(summary, f, indent=4)
        except PermissionError:
            show_notification(
                title=f'{self.cls_name}.dump_current_status',
                message='保存に失敗しました。アクセスが拒否されました。'
            )
        else:
            show_notification(
                title=f'{self.cls_name}.dump_current_status',
                message=f'{fpath}に保存しました。'
                )

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
        WOTB_HEIGHT = Screen.PrimaryScreen.WorkingArea.Height
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
        WOTB_WIDTH = Screen.PrimaryScreen.WorkingArea.Width
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

def main() -> None:
    try:
        window = tk.Tk()
        style = ttkthemes.ThemedStyle(master=window, theme='black')
        style.map(
            'Treeview',
            foreground=[Elm for Elm in style.map("Treeview", query_opt='foreground') if Elm[:2] != ("!disabled", "!selected")]
            )
        MainWindow(window, 340, 264)
        window.mainloop()
    except:
        pass
    OpenHardWareMonitor.close()
    sys.exit(0)


if __name__ == '__main__':
    main()
