# PythonMonitor
<div style="text-align: center;"><p>
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/64affa37-bec0-bd4b-e086-132e0534efd5.png" ></p></div>

趣味で作ったアプリケーションです。[qiitaで記事](https://qiita.com/ppza53893/items/6bd3c5923376f348889b)にもしてます。


# テーブル内容
<div style="text-align: center;">
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/83454a17-7cb8-b03c-35a5-c25e84be3278.jpeg"></div>

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
|GPU Fan|GPUファンの回転速度を表示します。`nvidia-smi`があれば色付きになります。|
|GPU Power|現在のGPUの消費電力を表示します。`nvidia-smi`があれば色付きになります。|
|GPU RAM Usage|現在のGPUのメモリ使用率を表示します。|
|GPU Temperature|GPUの温度を表示します。|

## コマンド

<div style="text-align: center;">
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/f661fdf9-02e6-47e8-480b-47403374fe1e.jpeg"></div>

- Ctrl + Q …プログラムを終了します
- Ctrl + P …最前面に固定を解除します。デフォルトでは固定されていません。再び押すと元に戻ります。
- Ctrl + H …ヒントを表示(上図)します。起動時は必ず出てきます。
- Ctrl + S …現在のステータスをjson形式で保存します。保存先はpyファイルと同じ場所です。
- Ctrl + {J, M, H, K} …ウィンドウを移動します。Ctrl+Jで上へ、Ctrl+Mで下、Ctrl+Hで左端、Ctrl+Kで右端に行きます。
- Ctrl + R …ウィンドウが半透明になります。再び押すと解除されます。
- Ctrl + B …更新間隔を0.5sにします。起動時は1s間隔です。再び押すと元に戻ります。
- Ctrl + T …タイトル表示を「CPU使用率、CPU温度」、または通常のタイトルに切り替えます。

## リアルタイムでグラフ表示

<div style="text-align: center;">
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/355856f3-5f60-5ae0-d796-7a7f691a5b05.jpeg"></div>

`Value`が文字列でないものについては、右クリックすると「選択中のデータのグラフを表示」というものを押すことができます。
これをクリックすると、別ウィンドウでグラフが表示されます。

<div style="text-align: center;">
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/12929ddd-1770-63b7-35e2-eff04dd09a34.jpeg"></div>

複数選択状態であれば、まとめて表示されます。

<div style="text-align: center;">
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/2dbd6792-fe1f-049d-b55d-afd0d3b6f358.jpeg"></div>

ちなみに、こちらにもコマンドがあり、`Ctrl + P`と`Ctrl + R`があります。意味についてはメインウィンドウと同様です。

### 注意点
- Pythonの使用上、グラフが多すぎるとラグが発生します。メインウィンドウのデータ更新はほぼ1s間隔ですが、グラフが多いと結構重くなるので注意してください。
- グラフウィンドウは最大10個まで、1画面で表示できるグラフの最大数も10個です。


# 導入手順
Python 3.7、3.8で動作確認済みです。3.9はpythonnetが動かないため、Anaconda等で3.7 or 3.8の環境を作ってください。

```shell
pip install pythonnet matplotlib
```


## 1.DLLのダウンロード
[Open Hardware Monitor](https://openhardwaremonitor.org/downloads/)をダウンロードして、解凍した中身の`OpenHardwareMonitorLib`をpythonコードのあるディレクトリ上に置きます

### 任意
- [azure theme](https://github.com/rdbende/Azure-ttk-theme): 同じディレクトリ上に置いておくとテーマが上のスクリーンショットのようになります
- アイコン(任意): `shared.ico`という名前で同じディレクトリ上に置いておくと、アイコンが変わります。

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

# バグ
- ~~バッテリー搭載PCについて、初回起動時に電源コードを抜くとなぜかエラーもなく勝手に終了します。理由は分かってないです…~~ タスクスケジューラの設定で解決します。
- マルチGPUは手元に環境がないので、もしかしたらエラーが出るかもしれません。

何かバグがあればissueに投げてください。時間があれば直していきます。