# PythonMonitor
<div style="text-align: center;"><p>
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/1c69fe83-4cfc-85a7-beca-d78a443841a8.png" ></p></div>

趣味で作ったアプリケーションです。[qiitaで記事](https://qiita.com/ppza53893/items/6bd3c5923376f348889b)にもしてるので、是非見ていただければと思います。


# テーブル内容

<div style="text-align: center;">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/c124a5c2-8b6e-6e9d-0fad-aa6081f1991c.jpeg"></div>

(※[azureテーマ](https://github.com/rdbende/Azure-ttk-theme)を使用しています。gitの方は入っていないので、各自でダウンロードして同じディレクトリ上においてください。)

|名前|内容|
|---|---|
|AC Status|ACプラグが接続されているかどうかの状態です。<br>- Offline: 未接続<br>- Online: 接続<br>Unknown: 不明|
|Battery|バッテリーの残量<br>未接続かつ残り35%を切ると、接続してくださいという通知を、<br>接続かつ95%以上のときは十分に充電されている<br>というのをWindowsの通知センターを経由して送ります。|
|Battery status|バッテリーの残量をがどの程度かを表示します。<br>詳細は[こちら(`BatteryFlag`)](https://docs.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-system_power_status#members)|
|CPU temperature|CPUの温度を表示します。|
|CPU usage|CPU使用率。クリックで各スレッドの使用率も表示します|
|CPU bus|CPUバス速度を表示します。クリックで各コアのクロック周波数も表示します。|
|CPU power|CPUの消費電力を表示します。クリックで各コアの消費電力も表示します。|
|Disk usage|Cドライブの使用率を表示します。|
|Memory|メモリの使用率を表示します。|
|Running PIDs|起動中のプログラムの数を表示します。|
|WiFi usage(In/Out)|Wifiの使用率をKB/s単位で表示します。|

Nvidia GPU搭載の場合は上段3つが次のようになります。バッテリー搭載PCであれば一応選択もできるようにしています。


|名前|内容|
|---|---|
|GPU Fan|GPUファンの回転速度を表示します。|
|GPU power|現在のGPUの消費電力を表示します。|
|GPU temperature|GPUの温度を表示します。|


## コマンド

<div style="text-align: center;">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;
<img src="https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/783413/bef2127c-7ef9-c09b-068f-817061d724c4.jpeg"></div>

- Ctrl + Q …プログラムを終了します
- Ctrl + P …最前面に固定を解除します。デフォルトでは固定されていません。再び押すと元に戻ります。
- Ctrl + H …ヒントを表示(上図)します。起動時は必ず出てきます。
- Ctrl + S …現在のステータスをjson形式で保存します。保存先はpyファイルと同じ場所です。
- Ctrl + {J, M, H, K} …ウィンドウを移動します。Ctrl+Jで上へ、Ctrl+Mで下、Ctrl+Hで左端、Ctrl+Kで右端に行きます。
- Ctrl + R …ウィンドウが半透明になります。再び押すと解除されます。
- Ctrl + B …更新間隔を0.5sにします。起動時は1s間隔です。再び押すと元に戻ります。

# 導入手順
Python 3.7で動作確認済みです。3.9はpythonnetが動かないため、Anaconda等で3.7 or 3.8の環境を作ってください。

```shell
pip install pythonnet
```

## 1.DLLのダウンロード
[Open Hardware Monitor](https://openhardwaremonitor.org/downloads/)をダウンロードして、解凍した中身の`OpenHardwareMonitorLib`をpythonコードのあるディレクトリ上に置きます

## 2. 管理者権限で起動
ここについては色々あります。一応3パターン紹介しておきます

### 1. cmdを管理者権限で起動してpythonから`pytaskmgr.py`を実行

### 2. タスクスケジューラを使ってログオン時に起動するようにする
登録とかは[ここ](https://pc-karuma.net/windows-10-task-schedule-without-uac-prompt/)を参考に設定してください。<br>プログラムの操作ではプログラムを`pythonw.exe`(Anaconda使っているひとは環境の`pythonw.exe`の絶対パス)に、引数は`pytaskmgr.py`のパスを指定します。
### 3. ショートカットを使う
バッチファイルで

```bash
pythonw.exe pytaskmgr.py
```
を作成し(引数等については1と同じ)作製したbatファイルのショートカットを作成、ショートカットの詳細設定で管理者権限で起動にチェックを入れます。

# バグ
- バッテリー搭載PCについて、初回起動時にACプラグを抜くとなぜかエラーもなく勝手に終了します。理由は分かってないです…
- マルチGPUは手元に環境がないので、もしかしたら動かないかもしれません。
