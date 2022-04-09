# PythonMonitor
<div style="text-align: center;"><p>
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/64affa37-bec0-bd4b-e086-132e0534efd5.png" ></p></div>

趣味で作ったアプリケーションです。[qiitaで記事](https://qiita.com/ppza53893/items/6bd3c5923376f348889b)にもしてます。


# 特徴
- バッテリー、CPU情報、ネットワーク情報などが一度の画面で見れる
  - NvidiaGPU搭載のPCならGPUの電力やファン速度、温度なども表示
- 使用率がカラーでわかる(※一部)
- グラフ化に対応
- Windowsのテーマに追従してテーマが変わる(設定で無効可)

# 見本

<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/d297adfe-5daa-5993-249c-24803713e554.jpeg">&emsp;&emsp;<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/d447e161-7bcf-3486-416e-d81bd7a947c7.jpeg">

|名前|内容|
|---|---|
|AC Status|ACプラグが接続されているかどうかの状態です。<br>- Offline: 未接続<br>- Online: 接続<br>Unknown: 不明|
|Battery|バッテリーの残量<br>未接続かつ残り35%を切ると、接続してくださいという通知を、<br>接続かつ95%以上のときは十分に充電されている<br>というのをWindowsの通知センターを経由して送ります。|
|Battery Status|バッテリーの残量をがどの程度かを表示します。<br>詳細は[こちら(`BatteryFlag`)](https://docs.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-system_power_status#members)|
|CPU Temperature|CPUの温度を表示します。画像中は1つだけですが、CPUによってはクリックでコア毎の温度も表示します。|
|CPU Usage|CPU使用率。クリックで各スレッドの使用率も表示します|
|CPU Bus|CPUバス速度を表示します。クリックで各コアのクロック周波数も表示します。|
|CPU Power|CPUの消費電力を表示します。クリックで各コアの消費電力も表示します。|
|Disk Usage|Cドライブの使用率を表示します。|
|Memory Usage|メモリの使用率を表示します。|
|Running Processes|起動中のプログラムの数を表示します。|
|Network(Sent / Received)|ネットワーク使用率(無線 or 有線)をKB/s単位で表示します。|

Nvidia GPU搭載の場合は上段3つが次のようになります。バッテリー搭載PCであれば一応選択もできるようにしています。

|名前|内容|
|---|---|
|GPU Fan|GPUファンの回転速度を表示します。<br>`nvidia-smi`があれば色付きになります(pythonwからは無効)。|
|GPU Power|現在のGPUの消費電力を表示します。<br>`nvidia-smi`があれば色付きになります(pythonwからは無効)|
|GPU RAM Usage|現在のGPUのメモリ使用率を表示します。|
|GPU Temperature|GPUの温度を表示します。|

## コマンド

<div style="text-align: center;">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/72b6e408-58f0-6a2a-c43a-2d7255715b0f.jpeg"></div>

- Ctrl + Q …プログラムを終了します
- Ctrl + P …最前面に固定を解除します。デフォルトでは固定されていません。再び押すと元に戻ります。
- Ctrl + H …ヒントを表示(上図)します。起動時は必ず出てきます。
- Ctrl + S …現在のステータスをjson形式で保存します。保存先はpyファイルと同じ場所です。
- Ctrl + {J, M, H, K} …ウィンドウを移動します。Ctrl+Jで上へ、Ctrl+Mで下、Ctrl+Hで左端、Ctrl+Kで右端に行きます。
- Ctrl + R …ウィンドウが半透明になります。再び押すと解除されます。
- Ctrl + B …更新間隔を0.5sにします。起動時は1s間隔です。再び押すと元に戻ります。
- Ctrl + T …タイトル表示を「CPU使用率、CPU温度」、または通常のタイトルに切り替えます。

## グラフ表示

<div style="text-align: center;">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/01249515-b72b-3850-8a2b-3109657cfa79.jpeg"></div>

`Value`が文字列でないものについては、右クリックすると「選択中のデータのグラフを表示」というものを押すことができます。
これをクリックすると、別ウィンドウでグラフが表示されます。

<div style="text-align: center;">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/cda9ae28-72b9-1043-f1a4-8cd72efe586f.jpeg"></div>

複数選択状態であれば、まとめて表示されます。

<div style="text-align: center;">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/6ee96c59-3e37-92f5-16dd-64373ac85ae1.jpeg"></div>

ちなみに、こちらにもコマンドがあり、`Ctrl + P`と`Ctrl + R`があります。意味についてはメインウィンドウと同様です。

### 注意点
- Pythonの仕様([GIL](https://docs.python.org/ja/3/glossary.html#term-global-interpreter-lock))上、グラフが多すぎるとラグが発生します。メインウィンドウのデータ更新はほぼ1s間隔ですが、グラフが多いと結構重くなるので注意してください。
- グラフウィンドウは最大10個まで、1画面で表示できるグラフの最大数も10個です。


# 導入手順
Python 3.7、3.8で動作確認済みです。3.9はpythonnetが動かないため、Anaconda等で3.7 or 3.8の環境を作ってください。

```shell
pip install pythonnet matplotlib
```

## 1.DLLのダウンロード
[Open Hardware Monitor](https://openhardwaremonitor.org/downloads/)をダウンロードして、解凍した中身の`OpenHardwareMonitorLib`をpythonコードのあるディレクトリ上に置きます


## 2. 管理者権限で起動
ここについては色々あります。一応3パターン紹介しておきます

### 1. cmdを管理者権限で起動してpython(or pythonw)から`pytaskmgr.py`を実行

### 2. タスクスケジューラを使ってログオン時に起動するようにする
登録とかは[ここ](https://pc-karuma.net/windows-10-task-schedule-without-uac-prompt/)を参考に設定してください。<br>プログラムの操作ではプログラムを`pythonw.exe`(Anaconda使っているひとは環境の`pythonw.exe`の絶対パス)に、引数は`pytaskmgr.py`のパスを指定します。
(2021/10/29) ノートPCでこのアプリケーションを使う場合、タスクスケジューラの「コンピューターの電源がバッテリに切り替わった場合は停止する」はOFFにしてください。そうしないとACプラグを抜くと強制終了してしまいます。

### 3. ショートカットを使う
バッチファイルで

```bash
pythonw.exe pytaskmgr.py
```
を作成し(引数等については1と同じ)作製したbatファイルのショートカットを作成、ショートカットの詳細設定で管理者権限で起動にチェックを入れます。

# 設定
コマンドラインから起動する場合、オプションが選べます。

|名前|内容|
|---|---|
|`--gpu`|GPU使用率 (Engine 3D)も表示するかどうか設定します。値はPerformanceCounterからとってきているので、有効にした状態で起動すると更新間隔が遅くなります。<br><img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/90dabc7a-5bc8-1a38-596b-add7564e3a59.jpeg">|
|`--theme`|アプリのテーマを指定できます。種類は`light`, `dark`, `system`の3種類で、`system`は使っているwindowsのシステムに追従する形になります。<br>Light:<br><img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/be734fe7-f602-28d5-a51c-87cfa7255b73.jpeg">|


# 使ったこと
趣味をつめこんだのでいろいろバックでやってます。
- COMエラー回避(tkinter & clr & matplotlibで衝突するため)
    - `pytaskmgr.py`
- レジストリからの配色取得、Windowsのテーマ取得
    - モードに応じた自動配色(グラフも対応してます)
    - `src/systemAPI/registry.py`, `src/utils/table.py`
- Tkinterのスタイル改造
    -  `src/utils/table.py`
- 高Dpi対応
    -  `src/systemAPI/c_api.py`
-  Dpi変化によるサイズ(画面サイズ、フォント等も含め)の自動変化
    -  DPIの異なる画面に映る/画面の拡大を変化した後自動リサイズします
    -  `src/systemAPI/c_api.py`
-  管理者権限かの判断
    -  `src/windows.py`
- nvidia-smiからのデータ取得(色を付けるため、データの値はOpenhardwareMonitorからです。)
    - `src/systemAPI/gpu.py`
- GPU使用率の取得(PerformanceCounter + regex)
    - `src/systemAPI/gpu.py`
- ネットワーク速度取得
    - `src/systemAPI/network.py`
- バッテリー状態取得
    - `src/systemAPI/powerline.py`
- メッセージボックス表示
    - `src/systemAPI/win_forms.py`
- 表示するグラフ数に応じたレイアウト変更
    - `src/mpl_graph.py`

# バグ
- マルチGPUは手元に環境がないので、もしかしたらエラーが出るかもしれません。

何かバグがあればissueに投げてください。時間があれば直していきます。


# 今後
- 殆どがOpenHardwareMonitorに依存しているので、フルスクラッチで自分で書こうかなとも考えてます
- pythonでの限界を感じます…