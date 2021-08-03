import os
import ctypes
import sys
import tkinter as tk
import tkinter.ttk as ttk
import subprocess
from ctypes import windll
from ctypes.wintypes import BOOL, BYTE, DWORD

import psutil
import ttkthemes
from plyer import notification


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', BYTE),
        ('BatteryFlag', BYTE),
        ('BatteryLifePercent', BYTE),
        ('Reserved1', BYTE),
        ('BatteryLifeTime', DWORD),
        ('BatteryFullLifeTime', DWORD),
    ]


INIT_SIZE = windll.user32.GetSystemMetrics(0)
WIN_RESIZE_DETECT = False


class Window(tk.Frame):
    ICON = r'C:\ProgramData\Anaconda3\Menu\anaconda-navigator.ico'
    _PROC = [f'CPU #{i+1}' for i in range(psutil.cpu_count())]
    NAME = [
        'AC status',
        'Battery',
        'Battery status',
        'CPU']+_PROC+[
        'Disk usage',
        'Memory',
        'Running PIDs',
        'WiFi speed'
        ]
    _AC_STATUS = {
        '0': 'Offline',
        '1': 'Online',
        '255': 'Unknown'
    }
    _BATTERY_FLAG = {
        '0': 'Uncharged',
        '1': 'High',
        '2': 'Low',
        '4': 'Critical',
        '8': 'Charging',
        '9': 'Charging(High)',
        '10': 'Chargin(Low)',
        '12': 'Charging(Critical)',
        '128': 'Undefind',
    }
    BATTERY_ALERT_MIN = 30
    BATTERY_ALERT_MAX = 95

    def __init__(self, master: tk.Tk=None, width: int=640, height: int=480) -> None:
        super().__init__(master)
        self.master = master
        self.pack()

        self.battery_warn = False
        self.battery_full = False

        self.width = width
        self.height = height
        pos_w = INIT_SIZE - self.width
        pos_h = windll.user32.GetSystemMetrics(1) - 248
        pos = f'{self.width}x{self.height}+{pos_w}+{pos_h}'
        self.showtop = True
        self.battery_id = ''

        self.master.geometry(pos)
        self.master.overrideredirect(True)
        self.master.iconbitmap(self.ICON)
        self.master.bind('<Control-Key-q>', self.app_exit)
        self.master.bind('<Control-Key-p>', self.topmost)
        
        self.master.title('Process')
        self.master.attributes("-topmost", self.showtop)

        self._set_format()

        self.make_table()

        self.master.resizable(width=False, height=False)
        self.update()

    def _set_format(self):
        self._FMT = []
        for name in self.NAME:
            if name in ['Running PIDs', 'AC status', 'Battery status']:
                self._FMT.append('')
            elif name == 'WiFi speed':
                self._FMT.append('MB/s')
            else:
                self._FMT.append('%')

    def get_battery_status(self):
        status = SYSTEM_POWER_STATUS()
        status_p = ctypes.POINTER(SYSTEM_POWER_STATUS)
        GetSystemPowerStatus = windll.kernel32.GetSystemPowerStatus
        GetSystemPowerStatus.argtypes = [status_p]
        GetSystemPowerStatus.restype = BOOL
        GetSystemPowerStatus(ctypes.pointer(status))
        ret = {}
        for field, _ in status._fields_:
            if field == 'BatteryFlag':
                st = getattr(status, field)
                if st & 8 ==0 and st & 128 != 0:
                    field_set = 128
                else:
                    field_set = st
                ret[field] = field_set
            else:
                ret[field] = getattr(status, field)
        res = dict(
            (field, getattr(status, field)) for field, _ in status._fields_
        )
        return res

    def get_process(self) -> list:
        processes_ecpu = [psutil.cpu_percent()] + psutil.cpu_percent(percpu=True)
        bres = self.get_battery_status()
        battery_info = [
            self._AC_STATUS[str(bres['ACLineStatus'])],
            float(psutil.sensors_battery().percent),
            self._BATTERY_FLAG[str(bres['BatteryFlag'])],
        ]
        others = [
            psutil.disk_usage('/').percent,
            psutil.virtual_memory().percent,
            len(psutil.pids()),
            psutil.net_if_stats()['Wi-Fi'].speed
        ]
        return battery_info + processes_ecpu + others

    def make_table(self):
        self.tree = ttk.Treeview(self.master, height=13, columns=(1,2))

        self.tree.column('#0', width=self.width//2-20)
        self.tree.column(1, width=self.width//2-20)
        self.tree.column(2, width=40)

        self.tree.heading('#0', text='Name')
        self.tree.heading(1, text="Value")
        self.tree.heading(2, text="Unit")
        self.id_list = []
        processes = self.get_process()
        master_index = ''
        for idx, (name, proc, fmt) in enumerate(zip(self.NAME, processes, self._FMT)):
            if name in self._PROC:
                id = self.tree.insert(master_index, "end", tags=idx, text=name, values=(self.conv_proc_fmt(proc), fmt))
            else:
                id = self.tree.insert("", "end", tags=idx, text=name, values=(self.conv_proc_fmt(proc), fmt))
                if name == 'CPU':
                    master_index = id
                if name == 'Battery':
                    self.battery_id = id
                
            self.set_color(idx, name, proc)
            self.id_list.append(id)
        self.tree.pack()

    def conv_proc_fmt(self, proc):
        if isinstance(proc, float):
            proc_str = f'{proc:.1f}'
        else:
            proc_str = str(proc)
        return proc_str

    def set_color(self, tag, name, proc):
        if isinstance(proc, float):
            p = round(0xdf * proc/100)
            if name == 'Battery':
                cl = '#{:0>2X}{:>02X}{:>02X}'.format(0xdf, p, p)
            else:
                cl = '#{:0>2X}{:>02X}{:>02X}'.format(0xdf, 0xdf-p, 0xdf-p)
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
                cl = '#df0000'
        else:
            cl = 'white'
        self.tree.tag_configure(tagname=tag, foreground=cl)

    def update(self):
        global INIT_SIZE
        wsize = windll.user32.GetSystemMetrics(0)
        if wsize != INIT_SIZE:
            INIT_SIZE = wsize
            self.app_exit(0, winsize_changed=True)
        processes = self.get_process()
        for i, (idx, proc) in enumerate(zip(self.id_list, processes)):
            self.tree.set(idx, 1, value=self.conv_proc_fmt(proc))
            self.set_color(i, self.NAME[i], proc)
            if self.battery_id == idx:
                current = psutil.sensors_battery().percent
                charging = self.get_battery_status()['ACLineStatus']
                charging = True if charging == 1 else False
                if current <= self.BATTERY_ALERT_MIN and not charging and not self.battery_warn:
                    notification.notify(
                        title = '警告',
                        message = f'残りバッテリ―容量が{self.BATTERY_ALERT_MIN}%です。電源を接続してください。',
                        app_name = 'Python Monitor',
                        app_icon = self.ICON)
                    self.battery_warn = True
                elif current >= self.BATTERY_ALERT_MAX and charging and not self.battery_full:
                    notification.notify(
                        title = 'Info',
                        message = 'PCは十分に充電されています。',
                        app_name = 'Python Monitor',
                        app_icon = self.ICON)
                    self.battery_full = True
                elif current > self.BATTERY_ALERT_MIN and current < self.BATTERY_ALERT_MAX:
                    self.battery_full = False
                    self.battery_warn = False
        self.master.after(1000, self.update)
    
    def app_exit(self, event, **kwargs):
        global WIN_RESIZE_DETECT
        if 'winsize_changed' in kwargs:
            WIN_RESIZE_DETECT = True
        else:
            WIN_RESIZE_DETECT = False
        self.master.destroy()
    
    def topmost(self, *args, **kwargs):
        self.showtop = not self.showtop
        print('Switched to {}'.format(self.showtop))
        self.master.attributes("-topmost", self.showtop)

def main():
    try:
        while True:
            window = tk.Tk()
            style = ttkthemes.ThemedStyle(master=window, theme='black')
            style.map(
                'Treeview',
                foreground=[Elm for Elm in style.map("Treeview", query_opt='foreground') if Elm[:2] != ("!disabled", "!selected")]
                )
            Window(window, 300, 200)
            window.mainloop()
            if not WIN_RESIZE_DETECT:
                break
    except (KeyboardInterrupt, KeyError, psutil.Error) as e:
        print('Process end: ', e)
        sys.exit(0)

if __name__ == '__main__':
    subprocess.call('echo off', shell=True)
    subprocess.call('cls', shell=True)
    main()
