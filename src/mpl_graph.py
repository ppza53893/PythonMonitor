import dataclasses
import math
import os
import random
import tkinter as tk
import tkinter.ttk as ttk
from typing import Any, Dict, List, Union

try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except (ImportError, ModuleNotFoundError):
    has_mpl = False
else:
    has_mpl = True
    plt.rcParams['text.color'] = '0.9'
    plt.rcParams['figure.facecolor'] = '#333333'
    plt.rcParams['axes.facecolor'] = '#333333'
    plt.rcParams['axes.edgecolor'] = '#737373'
    plt.rcParams['xtick.color'] = '0.9'
    plt.rcParams['ytick.color'] = '0.9'
    cm = plt.get_cmap('gist_rainbow', 100)

from .gname import PYTASKMGR
from .systemAPI import info


__all__ = ["create_graph", "has_mpl"]


RUNNING_GRAPHS = 0
MAX_SHOW = 10

def create_graph(mainwindow: ttk.Frame, target_ids: List[str], icon: str) -> bool:
    if RUNNING_GRAPHS > MAX_SHOW:
        info("表示中のグラフが多すぎます。")
    elif len(target_ids) == 1:
        MplGraph(mainwindow, target_ids[0], icon)
    elif len(target_ids) > MAX_SHOW:
        info("同時に表示可能なグラフ数は10個までです。")
    else:
        MplGraphs(mainwindow, target_ids, icon)


def count_running_graphs():
    global RUNNING_GRAPHS
    RUNNING_GRAPHS += 1


def remove_running_graphs():
    global RUNNING_GRAPHS
    RUNNING_GRAPHS -= 1


def get_title(data: Dict[str, Any]) -> str:
    cur = data['values'][-1]
    if data['type_'] is float:
        cur = round(cur, 1)
    elif data['type_'] is int:
        cur = int(cur)
    title = data['name'].name + ': {} {}'.format(cur, data['name'].unit)
    return title


@dataclasses.dataclass
class MplGraphBase:
    mainwindow : ttk.Frame
    target_ids: Union[str, List[str]]
    icon: str

    def __post_init__(self) -> None:
        count_running_graphs()
        self.master = tk.Toplevel(master=self.mainwindow.master)
        if os.path.exists(self.icon):
            self.master.iconbitmap(self.icon)
        self.master.geometry('360x120')
        self.master.protocol("WM_DELETE_WINDOW", self.app_exit)
        self.master.bind('<Control-Key-r>', self.switch_window_transparency)
        self.master.bind('<Control-Key-p>', self.switch_topmost)

        # keep tops
        self.showtop = False

        # option
        self.transparent = False
        
        # x data
        self.x_data = list(range(30))
        
        self.initialize_graph()
        self.update_data()

    def initialize_graph(self) -> None:
        raise NotImplementedError

    def update_data(self) -> None:
        raise NotImplementedError

    def plot(self, ax: plt.Axes, data: Dict[str, Any], color_key: int) -> None:
        ax.cla()
        ax.plot(self.x_data, data['values'], '-', color=cm(color_key))
        ax.fill_between(self.x_data, data['values'], color=cm(color_key-1), alpha=0.2)
        ax.set_xlim(0, 29)
        if data['name'].unit == '%' or data['name'].unit == '°C':
            ax.set_ylim(0, 100)

    def app_exit(self, *args, **kwargs):
        remove_running_graphs()
        if hasattr(self, "fig"):
            plt.close(self.fig)
        self.master.destroy()

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
    

class MplGraphs(MplGraphBase):
    def initialize_graph(self):
        table_length = len(self.target_ids)
        for d in [2, 3]:
            if table_length % d == 0:
                self.rows = table_length // d
                self.cols = d
                break
        if not hasattr(self, "rows"):
            self.rows = math.ceil(table_length / 3)
            self.cols = 3
        
        self.master.geometry(f'{360*self.cols}x{180*self.rows}')
        self.master.title(PYTASKMGR)

        self.fig, self.axs = plt.subplots(nrows=self.rows, ncols=self.cols, sharex=True)
        if self.axs.ndim == 1:
            self.axs = self.axs[np.newaxis,:]
        self.graph = FigureCanvasTkAgg(self.fig, master=self.master)
        canvas = self.graph.get_tk_widget()
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        self.key_list = [random.randint(1, 100) for _ in range(table_length)]
        for i in range(self.rows):
            for j in range(self.cols):
                self.axs[i, j].get_xaxis().set_visible(False)

    def update_data(self):
        tables = self.mainwindow.data_table
        row_count = 0
        for i, tid in enumerate(self.target_ids):
            axes = self.axs[row_count, i % self.cols]
            table = tables[tid]
            self.plot(axes, table, self.key_list[i])
            axes.set_title(get_title(table), fontsize=8)

            if (i+1) % self.cols == 0:
                row_count += 1
        
        self.graph.draw()
        self.master.after(self.mainwindow.cycle, self.update_data)

    def switch_topmost(self, *args, **kwargs) -> None:
        super().switch_topmost(*args, **kwargs)
        if self.showtop:
            self.master.title(f'*{PYTASKMGR}')
        else:
            self.master.title(PYTASKMGR)


class MplGraph(MplGraphBase):
    def initialize_graph(self):
        self.fig, self.ax = plt.subplots()
        self.graph = FigureCanvasTkAgg(self.fig, master=self.master)
        canvas = self.graph.get_tk_widget()
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.ax.get_xaxis().set_visible(False)
        self.key_idx = random.randint(1, 100)

    def update_data(self):       
        data = self.mainwindow.data_table[self.target_ids]
        self.plot(self.ax, data, self.key_idx)

        title = get_title(data)
        if self.showtop:
            title = '* ' + title
        self.master.title(title)
        self.graph.draw()
        self.master.after(self.mainwindow.cycle, self.update_data)
