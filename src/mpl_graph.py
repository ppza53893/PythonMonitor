import dataclasses
import itertools
import math
import os
import random
import tkinter as tk
import tkinter.ttk as ttk
from typing import List

try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.collections import PolyCollection
except (ImportError, ModuleNotFoundError):
    has_mpl = False
else:
    has_mpl = True
    cm = plt.get_cmap('gist_rainbow', 100)

from .gname import PYTASKMGR
from .systemAPI import info

__all__ = ["create_graph", "has_mpl", "use_dark_style"]


RUNNING_GRAPHS = 0
MAX_SHOW = 10

def create_graph(mainwindow: ttk.Frame, target_ids: List[str], icon: str) -> bool:
    if RUNNING_GRAPHS > MAX_SHOW:
        info("表示中のグラフが多すぎます。")
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


def use_dark_style():
    if has_mpl:
        plt.rcParams['text.color'] = '0.9'
        plt.rcParams['figure.facecolor'] = '#333333'
        plt.rcParams['axes.facecolor'] = '#333333'
        plt.rcParams['axes.edgecolor'] = '#737373'
        plt.rcParams['xtick.color'] = '0.9'
        plt.rcParams['ytick.color'] = '0.9'


@dataclasses.dataclass
class MplGraphs:
    """
    show realtime data graph.
    """
    mainwindow : ttk.Frame # pytaskmgr.py -> MainWindow
    target_ids: List[str]
    icon: str

    def __post_init__(self) -> None:
        count_running_graphs()
        self.master = tk.Toplevel(master=self.mainwindow.master)
        if os.path.exists(self.icon):
            self.master.iconbitmap(self.icon)
        self.master.protocol("WM_DELETE_WINDOW", self.app_exit)
        self.master.bind('<Control-Key-r>', self.switch_window_transparency)
        self.master.bind('<Control-Key-p>', self.switch_topmost)

        # keep tops
        # used: self.switch_topmost
        self.showtop = False

        # option
        # used: self.switch_window_transparency
        self.transparent = False
        
        # x data
        self.x_data = np.arange(30)
        self.x_data.flags.writeable = False # immutable

        self.show_title_flag = False

        table_length = len(self.target_ids)
        self.lines = [None] * table_length
        if table_length > 1:
            for d in [2, 3]:
                if table_length % d == 0:
                    self.rows = table_length // d
                    self.cols = d
                    break
            if not hasattr(self, "rows"):
                self.rows = math.ceil(table_length / 3)
                self.cols = 3
            self.title_at = 'axes'
            self.master.geometry(f'{360*self.cols}x{180*self.rows}')
        else:
            self.rows = self.cols = 1
            self.title_at = 'bar'
            self.master.geometry('360x120')

        # title(init)
        self.master.title(PYTASKMGR)

        self.initialize_graph()
        self.update_data()

    def initialize_graph(self):
        # create canvas
        self.fig, self.axs = plt.subplots(nrows=self.rows, ncols=self.cols, sharex=True)
        if isinstance(self.axs, np.ndarray):
            if self.axs.ndim == 1:
                self.axs = self.axs[np.newaxis,:]
        else:
            self.axs = np.array(self.axs, dtype='O').reshape(1,1)
        self.graph = FigureCanvasTkAgg(self.fig, master=self.master)
        self.graph.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        # setting
        table_length = len(self.target_ids)
        
        r1, r2 = itertools.tee(range(self.rows*self.cols))
        
        self.key_list = [random.randint(1, 100) for _ in r1]
        self.polys = [PolyCollection([], facecolors=cm(k-1), alpha=0.2) for k in self.key_list]

        # default axes settings
        row_count = 0
        for i in r2:
            axes = self.axs[row_count, i % self.cols]
            axes.add_collection(self.polys[i])
            # set xlim
            axes.set_xlim(0, 29)
            # xaxis -> invisible
            axes.get_xaxis().set_visible(False)
            # unused axes -> hide y axis label
            if i > table_length - 1:
                axes.get_yaxis().set_visible(False)
            if (i+1) % self.cols == 0:
                row_count += 1

    def update_data(self):
        tables = self.mainwindow.data_table
        row_count = 0
        for i, tid in enumerate(self.target_ids):
            axes = self.axs[row_count, i % self.cols]
            table = tables[tid]

            x = self.x_data
            y = table['values']

            # update y
            if self.lines[i] is None:
                self.lines[i] = axes.plot(
                    x, y,
                    '-',
                    color=cm(self.key_list[i]))[0]
            else:
                self.lines[i].set_ydata(y)
            
            # fill between x and y
            verts = [[
                [0, 0],
                *zip(x, y),
                [x[-1], 0]]]
            self.polys[i].set_verts(verts)
            
            # set y lim
            if table['percentage_range']:
                r = [0, 100]
            else:
                _mi, _ma = min(y), max(y)
                _mi = 0 if _mi < 1 else _mi -1
                _ma += 1
                r = [_mi, _ma]
            axes.set_ylim(r)
            
            # set title
            cur = table['values'][-1]
            if table['type_'] is float:
                cur = round(cur, 1)
            elif table['type_'] is int:
                cur = int(cur)
            table_title = table['name'].name + ': {} {}'.format(cur, table['name'].unit)
            if self.title_at == 'axes':
                axes.set_title(table_title, fontsize=8)
            else:
                if self.showtop:
                    table_title = '*' + table_title
                self.master.title(table_title)
                break
            
            # next row
            if (i+1) % self.cols == 0:
                row_count += 1

        self.graph.draw()
        self.master.after(self.mainwindow.cycle, self.update_data)

    def app_exit(self, *args, **kwargs):
        remove_running_graphs()
        plt.close(self.fig)
        self.master.destroy()

    def switch_topmost(self, *args, **kwargs) -> None:
        """ウィンドウ最前面固定の有効/無効"""
        self.showtop = not self.showtop
        self.master.attributes("-topmost", self.showtop)

        if self.title_at == 'axes':
            title = f'*{PYTASKMGR}' if self.showtop else PYTASKMGR
            self.master.title(title)

    def switch_window_transparency(self, *args, **kwargs):
        if self.transparent:
            alpha = 1.0
        else:
            alpha = 0.5
        self.transparent = not self.transparent
        self.master.attributes("-alpha",alpha)
